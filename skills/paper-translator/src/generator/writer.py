"""
文章生成模块
- 调用LLM生成初稿
- 支持Anthropic和OpenAI
"""

import os
from dataclasses import dataclass
from pathlib import Path
from string import Template

from anthropic import Anthropic
from openai import OpenAI

from ..parser.pdf_parser import PaperContent


@dataclass
class ArticleConfig:
    """文章生成配置"""
    language: str = "zh-CN"
    style: str = "通俗易懂、深入浅出"
    audience: str = "对AI感兴趣的技术爱好者"
    max_tokens: int = 8192


@dataclass
class GeneratedArticle:
    """生成的文章"""
    title: str
    content: str  # Markdown格式
    image_placeholders: list[dict]  # 需要配图的位置
    word_count: int
    paper_title: str


class ArticleWriter:
    """文章生成器"""

    def __init__(
        self,
        provider: str = "anthropic",
        model: str | None = None,
        api_key: str | None = None,
        prompts_dir: Path | str = "./prompts",
    ):
        self.provider = provider
        self.prompts_dir = Path(prompts_dir)

        if provider == "anthropic":
            self.model = model or "claude-sonnet-4-20250514"
            self.client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        elif provider == "openai":
            self.model = model or "gpt-4o"
            self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        else:
            raise ValueError(f"不支持的provider: {provider}")

        # 加载提示词模板
        self.translate_prompt = self._load_prompt("translate.md")

    def _load_prompt(self, filename: str) -> str:
        """加载提示词模板"""
        prompt_path = self.prompts_dir / filename
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        else:
            raise FileNotFoundError(f"提示词文件不存在: {prompt_path}")

    def generate(
        self,
        paper: PaperContent,
        config: ArticleConfig | None = None,
        citations: int | None = None,
    ) -> GeneratedArticle:
        """
        根据论文内容生成文章初稿

        Args:
            paper: 解析后的论文内容
            config: 文章配置
            citations: 论文引用量（可选）

        Returns:
            生成的文章
        """
        config = config or ArticleConfig()

        # 构建提示词
        prompt = self._build_prompt(paper, config, citations)

        print(f"📝 正在生成文章初稿...")
        print(f"   模型: {self.provider}/{self.model}")

        # 调用LLM
        content = self._call_llm(prompt, config.max_tokens)

        # 解析生成的内容
        article = self._parse_generated_content(content, paper.title)

        print(f"✅ 初稿生成完成")
        print(f"   标题: {article.title}")
        print(f"   字数: {article.word_count}")
        print(f"   配图位置: {len(article.image_placeholders)}处")

        return article

    def _build_prompt(
        self,
        paper: PaperContent,
        config: ArticleConfig,
        citations: int | None,
    ) -> str:
        """构建完整的提示词"""
        # 准备论文内容摘要
        paper_content = self._prepare_paper_content(paper)

        # 替换模板变量
        prompt = self.translate_prompt
        prompt = prompt.replace("{{title}}", paper.title)
        prompt = prompt.replace("{{authors}}", ", ".join(paper.authors[:10]))
        prompt = prompt.replace("{{date}}", paper.metadata.get("creationDate", "未知"))
        prompt = prompt.replace("{{citations}}", str(citations) if citations else "未知")
        prompt = prompt.replace("{{content}}", paper_content)

        # 添加配置信息
        config_text = f"""
## 写作配置
- 目标语言: {config.language}
- 写作风格: {config.style}
- 目标读者: {config.audience}
"""
        prompt = prompt.replace("## 论文信息", config_text + "\n## 论文信息")

        return prompt

    def _prepare_paper_content(self, paper: PaperContent) -> str:
        """准备论文内容（控制长度）"""
        parts = []

        # 摘要
        if paper.abstract:
            parts.append(f"## Abstract\n{paper.abstract}")

        # 主要章节
        for title, content in paper.sections.items():
            # 限制每个章节的长度
            truncated = content[:3000] + "..." if len(content) > 3000 else content
            parts.append(f"## {title}\n{truncated}")

        # 图表信息
        if paper.figures:
            fig_info = "\n## 论文图表\n"
            for fig in paper.figures[:10]:  # 最多10个图
                fig_info += f"- Figure {fig.index} (Page {fig.page_num})"
                if fig.caption:
                    fig_info += f": {fig.caption}"
                fig_info += "\n"
            parts.append(fig_info)

        full_content = "\n\n".join(parts)

        # 总长度控制（避免超出上下文限制）
        if len(full_content) > 30000:
            full_content = full_content[:30000] + "\n\n[内容已截断...]"

        return full_content

    def _call_llm(self, prompt: str, max_tokens: int) -> str:
        """调用LLM生成内容"""
        if self.provider == "anthropic":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text

        elif self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content

        raise ValueError(f"不支持的provider: {self.provider}")

    def _parse_generated_content(self, content: str, paper_title: str) -> GeneratedArticle:
        """解析LLM生成的内容"""
        import re

        # 提取标题（第一个#开头的行）
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1) if title_match else paper_title

        # 提取配图占位符
        image_placeholders = []
        placeholder_pattern = r"<!--\s*IMAGE:\s*(.+?)\s*-->"
        for match in re.finditer(placeholder_pattern, content):
            image_placeholders.append({
                "position": match.start(),
                "description": match.group(1),
                "placeholder": match.group(0),
            })

        # 计算字数（中文+英文单词）
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", content))
        english_words = len(re.findall(r"[a-zA-Z]+", content))
        word_count = chinese_chars + english_words

        return GeneratedArticle(
            title=title,
            content=content,
            image_placeholders=image_placeholders,
            word_count=word_count,
            paper_title=paper_title,
        )


if __name__ == "__main__":
    # 测试
    from ..parser.pdf_parser import parse_paper

    paper = parse_paper("https://arxiv.org/abs/1706.03762")
    writer = ArticleWriter()
    article = writer.generate(paper, citations=100000)
    print(f"\n{'='*50}")
    print(article.content[:1000])
