"""
论文翻译器 - 主流程编排
自动完成：论文解析 → 文章生成 → 反思润色 → 配图 → 发布
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from .parser import PaperParser
from .generator import ArticleWriter, ArticleRefiner
from .image import FigureExtractor, ImageGenerator
from .publisher import WeChatPublisher


@dataclass
class TranslatorConfig:
    """翻译器配置"""
    # LLM配置
    llm_provider: str = "anthropic"
    llm_model: str = "claude-sonnet-4-20250514"

    # 图片生成配置
    image_model: str = "google/gemini-2.0-flash-preview-image-generation"
    generate_cover: bool = True
    use_paper_figures: bool = True

    # 文章配置
    language: str = "zh-CN"
    style: str = "通俗易懂、深入浅出"
    audience: str = "对AI感兴趣的技术爱好者"

    # 输出配置
    output_dir: str = "./output"
    save_markdown: bool = True
    save_html: bool = True

    # 发布配置
    auto_publish: bool = False
    author: str = ""


class PaperTranslator:
    """论文翻译器主类"""

    def __init__(self, config: TranslatorConfig | None = None):
        self.config = config or TranslatorConfig()
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 初始化各模块
        self.parser = PaperParser(output_dir=self.output_dir)
        self.writer = ArticleWriter(
            provider=self.config.llm_provider,
            model=self.config.llm_model,
            prompts_dir=Path(__file__).parent.parent / "prompts",
        )
        self.refiner = ArticleRefiner(
            provider=self.config.llm_provider,
            model=self.config.llm_model,
            prompts_dir=Path(__file__).parent.parent / "prompts",
        )
        self.figure_extractor = FigureExtractor(
            output_dir=self.output_dir / "figures"
        )
        self.image_generator = ImageGenerator(
            model=self.config.image_model,
            output_dir=self.output_dir / "images",
        )

    def _insert_images_to_article(
        self,
        content: str,
        generated_images: list[dict],
    ) -> str:
        """
        将生成的配图插入到文章的占位符位置

        Args:
            content: 原始 Markdown 内容（包含 <!-- IMAGE: xxx --> 占位符）
            generated_images: 生成的图片列表

        Returns:
            插入图片后的 Markdown 内容
        """
        # 找出所有图片占位符
        placeholders = list(re.finditer(r"<!--\s*IMAGE:\s*(.+?)\s*-->", content))

        if not placeholders:
            print("   未发现图片占位符")
            return content

        # 按位置倒序替换（避免位置偏移）
        for i, match in enumerate(reversed(placeholders)):
            placeholder_text = match.group(0)
            description = match.group(1)
            start, end = match.span()

            # 选择对应的图片
            img_index = len(placeholders) - 1 - i
            if img_index < len(generated_images):
                img = generated_images[img_index]
                img_path = img["path"]
                img_desc = img.get("description", description)

                # 替换为 Markdown 图片语法
                img_markdown = f"\n\n![{img_desc}]({img_path})\n\n"
                content = content[:start] + img_markdown + content[end:]
            else:
                # 如果图片不够，移除占位符
                print(f"   ⚠️ 图片不足，移除占位符: {description}")
                content = content[:start] + content[end:]

        return content

    def translate(
        self,
        paper_url: str,
        citations: int | None = None,
        publish: bool | None = None,
    ) -> dict:
        """
        执行完整的论文翻译流程

        Args:
            paper_url: 论文URL
            citations: 引用量（可选）
            publish: 是否发布到公众号

        Returns:
            包含所有输出的字典
        """
        print("=" * 60)
        print("🚀 论文翻译器启动")
        print("=" * 60)

        result = {
            "paper_url": paper_url,
            "success": False,
            "outputs": {},
        }

        try:
            # 1. 解析论文
            print("\n📄 [1/5] 解析论文...")
            paper = self.parser.parse(paper_url)
            result["paper_title"] = paper.title
            result["outputs"]["pdf_path"] = str(paper.pdf_path)

            # 2. 生成初稿
            print("\n📝 [2/5] 生成初稿...")
            from .generator.writer import ArticleConfig
            article_config = ArticleConfig(
                language=self.config.language,
                style=self.config.style,
                audience=self.config.audience,
            )
            draft = self.writer.generate(paper, article_config, citations)

            # 保存初稿
            if self.config.save_markdown:
                draft_path = self.output_dir / "draft.md"
                draft_path.write_text(draft.content, encoding="utf-8")
                result["outputs"]["draft_path"] = str(draft_path)

            # 3. 反思润色
            print("\n🔍 [3/5] 反思润色...")
            refined = self.refiner.refine(draft)

            result["article_title"] = refined.title
            result["word_count"] = refined.word_count

            # 4. 处理配图
            print("\n🎨 [4/5] 处理配图...")
            images = []
            article_images = []  # 用于插入文章的图片（不包括封面）

            # 提取论文图表
            if self.config.use_paper_figures and paper.figures:
                print("   提取论文图表...")
                figure_results = self.figure_extractor.extract_all_figures(paper)
                for fig, path in figure_results:
                    images.append({"type": "paper_figure", "path": str(path)})
                    # 论文图表可以插入文章
                    article_images.append({
                        "type": "paper_figure",
                        "path": str(path),
                        "description": fig.caption or f"Figure {fig.index}",
                    })

            # 生成封面图
            cover_path = None
            if self.config.generate_cover:
                print("   生成封面图...")
                try:
                    cover = self.image_generator.generate_cover(
                        title=refined.title,
                        topic="AI/Machine Learning",
                    )
                    cover_path = cover.path
                    images.append({"type": "cover", "path": str(cover_path)})
                    # 封面不插入文章正文
                except Exception as e:
                    print(f"   ⚠️ 封面生成失败: {e}")

            # 根据润色建议生成配图
            for suggestion in refined.image_suggestions[:3]:  # 最多3张
                if suggestion.type == "ai_generated" and suggestion.prompt:
                    print(f"   生成配图: {suggestion.description[:30]}...")
                    try:
                        img = self.image_generator.generate(suggestion.prompt)
                        img_info = {
                            "type": "ai_generated",
                            "path": str(img.path),
                            "description": suggestion.description,
                        }
                        images.append(img_info)
                        article_images.append(img_info)
                    except Exception as e:
                        print(f"   ⚠️ 配图生成失败: {e}")

            # 插入图片到文章中
            print(f"   插入 {len(article_images)} 张图片到文章...")
            final_content = self._insert_images_to_article(
                refined.content,
                article_images,
            )

            # 保存润色后的文章（含图片）
            if self.config.save_markdown:
                refined_path = self.output_dir / "article.md"
                refined_path.write_text(final_content, encoding="utf-8")
                result["outputs"]["article_path"] = str(refined_path)

            result["outputs"]["images"] = images

            # 5. 发布到公众号
            should_publish = publish if publish is not None else self.config.auto_publish

            if should_publish:
                print("\n📤 [5/5] 发布到公众号...")

                if not cover_path:
                    # 如果没有封面图，用第一张论文图
                    if paper.figures and paper.figures[0].image_path:
                        cover_path = paper.figures[0].image_path
                    else:
                        print("   ⚠️ 没有封面图，跳过发布")
                        should_publish = False

                if should_publish and cover_path:
                    try:
                        publisher = WeChatPublisher()
                        pub_result = publisher.publish_article(
                            title=refined.title,
                            md_content=final_content,  # 使用插入图片后的内容
                            cover_image=cover_path,
                            author=self.config.author,
                            source_url=paper_url,
                        )
                        result["publish_result"] = {
                            "success": pub_result.success,
                            "media_id": pub_result.media_id,
                            "error": pub_result.error,
                        }
                    except Exception as e:
                        print(f"   ❌ 发布失败: {e}")
                        result["publish_result"] = {"success": False, "error": str(e)}
            else:
                print("\n⏭️  [5/5] 跳过发布（未启用）")

            result["success"] = True

        except Exception as e:
            print(f"\n❌ 翻译失败: {e}")
            result["error"] = str(e)
            import traceback
            traceback.print_exc()

        # 总结
        print("\n" + "=" * 60)
        if result["success"]:
            print("✅ 翻译完成！")
            print(f"   标题: {result.get('article_title', 'N/A')}")
            print(f"   字数: {result.get('word_count', 'N/A')}")
            print(f"   输出目录: {self.output_dir}")
        else:
            print("❌ 翻译失败")
        print("=" * 60)

        return result


def load_config(config_path: str | None = None) -> TranslatorConfig:
    """从文件加载配置"""
    if config_path is None:
        # 查找默认配置文件
        for path in ["config/config.local.yaml", "config/config.yaml"]:
            if Path(path).exists():
                config_path = path
                break

    if config_path and Path(config_path).exists():
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return TranslatorConfig(
            llm_provider=data.get("llm", {}).get("provider", "anthropic"),
            llm_model=data.get("llm", {}).get("model", "claude-sonnet-4-20250514"),
            image_model=data.get("image", {}).get("model", "gemini-image"),
            generate_cover=data.get("article", {}).get("generate_cover", True),
            use_paper_figures=data.get("article", {}).get("use_paper_figures", True),
            language=data.get("article", {}).get("language", "zh-CN"),
            style=data.get("article", {}).get("style", "通俗易懂、深入浅出"),
            audience=data.get("article", {}).get("audience", "对AI感兴趣的技术爱好者"),
            output_dir=data.get("output", {}).get("dir", "./output"),
            save_markdown=data.get("output", {}).get("save_markdown", True),
            save_html=data.get("output", {}).get("save_html", True),
        )

    return TranslatorConfig()


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="论文翻译器 - 自动将论文转化为公众号文章",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 翻译arXiv论文
  python -m src.main https://arxiv.org/abs/1706.03762

  # 指定引用量
  python -m src.main https://arxiv.org/abs/1706.03762 --citations 100000

  # 翻译并发布到公众号
  python -m src.main https://arxiv.org/abs/1706.03762 --publish

  # 使用自定义配置
  python -m src.main https://arxiv.org/abs/1706.03762 --config config/my_config.yaml
        """,
    )

    parser.add_argument("url", help="论文URL（arXiv或PDF直链）")
    parser.add_argument("--citations", "-c", type=int, help="论文引用量")
    parser.add_argument("--publish", "-p", action="store_true", help="发布到公众号草稿")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--output", "-o", help="输出目录")

    args = parser.parse_args()

    # 加载配置
    config = load_config(args.config)

    if args.output:
        config.output_dir = args.output

    # 创建翻译器并执行
    translator = PaperTranslator(config)
    result = translator.translate(
        paper_url=args.url,
        citations=args.citations,
        publish=args.publish,
    )

    # 返回状态码
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
