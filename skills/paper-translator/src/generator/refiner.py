"""
文章润色模块
- 反思推理，优化文章质量
- 生成配图建议
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path

from anthropic import Anthropic
from openai import OpenAI

from .writer import GeneratedArticle


@dataclass
class ImageSuggestion:
    """配图建议"""
    position: int  # 在文章中的位置
    type: str  # "paper_figure" | "ai_generated"
    description: str  # 图片描述
    prompt: str  # AI生图的prompt（如果需要）
    paper_figure_index: int | None = None  # 论文原图索引


@dataclass
class RefinedArticle:
    """润色后的文章"""
    title: str
    content: str
    review_notes: str  # 审核意见
    image_suggestions: list[ImageSuggestion]
    word_count: int
    improvements: list[str]  # 改进点列表


class ArticleRefiner:
    """文章润色器"""

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
        self.refine_prompt = self._load_prompt("refine.md")

    def _load_prompt(self, filename: str) -> str:
        """加载提示词模板"""
        prompt_path = self.prompts_dir / filename
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        else:
            raise FileNotFoundError(f"提示词文件不存在: {prompt_path}")

    def refine(
        self,
        article: GeneratedArticle,
        max_tokens: int = 8192,
    ) -> RefinedArticle:
        """
        润色文章

        Args:
            article: 初稿文章
            max_tokens: 最大生成token数

        Returns:
            润色后的文章
        """
        print(f"🔍 正在进行反思润色...")
        print(f"   原文字数: {article.word_count}")

        # 构建提示词
        prompt = self.refine_prompt.replace("{{article}}", article.content)

        # 调用LLM
        response = self._call_llm(prompt, max_tokens)

        # 解析响应
        refined = self._parse_response(response, article)

        print(f"✅ 润色完成")
        print(f"   新字数: {refined.word_count}")
        print(f"   改进点: {len(refined.improvements)}处")
        print(f"   配图建议: {len(refined.image_suggestions)}处")

        return refined

    def _call_llm(self, prompt: str, max_tokens: int) -> str:
        """调用LLM"""
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

    def _parse_response(self, response: str, original: GeneratedArticle) -> RefinedArticle:
        """解析LLM响应"""
        # 分割响应的各个部分
        sections = self._split_response_sections(response)

        # 提取审核意见
        review_notes = sections.get("review", "")

        # 提取润色后的文章
        content = sections.get("article", response)

        # 提取改进点
        improvements = self._extract_improvements(review_notes)

        # 提取配图建议
        image_suggestions = self._extract_image_suggestions(sections.get("images", ""))

        # 提取标题
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1) if title_match else original.title

        # 计算字数
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", content))
        english_words = len(re.findall(r"[a-zA-Z]+", content))
        word_count = chinese_chars + english_words

        return RefinedArticle(
            title=title,
            content=content,
            review_notes=review_notes,
            image_suggestions=image_suggestions,
            word_count=word_count,
            improvements=improvements,
        )

    def _split_response_sections(self, response: str) -> dict[str, str]:
        """分割响应的各个部分"""
        sections = {}

        # 查找审核意见部分
        review_match = re.search(
            r"(?:##?\s*)?(?:1\.\s*)?(?:\*\*)?审核意见(?:\*\*)?[：:]*\s*\n(.*?)(?=(?:##?\s*)?(?:2\.\s*)?(?:\*\*)?润色后|$)",
            response,
            re.DOTALL | re.IGNORECASE,
        )
        if review_match:
            sections["review"] = review_match.group(1).strip()

        # 查找润色后的文章部分
        article_match = re.search(
            r"(?:##?\s*)?(?:2\.\s*)?(?:\*\*)?润色后的?完整文章(?:\*\*)?[：:]*\s*\n(.*?)(?=(?:##?\s*)?(?:3\.\s*)?(?:\*\*)?配图建议|$)",
            response,
            re.DOTALL | re.IGNORECASE,
        )
        if article_match:
            sections["article"] = article_match.group(1).strip()
        else:
            # 尝试提取Markdown内容
            md_match = re.search(r"```markdown\n(.*?)```", response, re.DOTALL)
            if md_match:
                sections["article"] = md_match.group(1).strip()

        # 查找配图建议部分
        images_match = re.search(
            r"(?:##?\s*)?(?:3\.\s*)?(?:\*\*)?配图建议(?:\*\*)?[：:]*\s*\n(.*?)$",
            response,
            re.DOTALL | re.IGNORECASE,
        )
        if images_match:
            sections["images"] = images_match.group(1).strip()

        return sections

    def _extract_improvements(self, review_notes: str) -> list[str]:
        """提取改进点"""
        improvements = []

        # 匹配列表项
        for match in re.finditer(r"[-•*]\s*(.+)", review_notes):
            improvement = match.group(1).strip()
            if improvement and len(improvement) > 5:
                improvements.append(improvement)

        # 匹配编号列表
        for match in re.finditer(r"\d+[.、)]\s*(.+)", review_notes):
            improvement = match.group(1).strip()
            if improvement and len(improvement) > 5:
                improvements.append(improvement)

        return improvements

    def _extract_image_suggestions(self, images_section: str) -> list[ImageSuggestion]:
        """提取配图建议"""
        suggestions = []

        if not images_section:
            return suggestions

        # 解析配图建议
        # 支持多种格式：
        # 1. 位置：xxx，描述：xxx，Prompt：xxx
        # 2. - 描述：xxx，Prompt：xxx
        # 3. 1. 描述 / Prompt: xxx

        lines = images_section.split("\n")
        current_suggestion = {}

        for line in lines:
            line = line.strip()

            # 如果是空行，保存当前建议并重置
            if not line:
                if current_suggestion and current_suggestion.get("description"):
                    suggestions.append(self._create_suggestion(current_suggestion))
                    current_suggestion = {}
                continue

            # 跳过标题行
            if line.startswith("#") or "配图建议" in line:
                continue

            # 检测新的建议项（编号或列表标记）
            is_new_item = re.match(r"^(\d+[.、)]|[-*•])\s", line)
            if is_new_item:
                # 保存上一个建议
                if current_suggestion and current_suggestion.get("description"):
                    suggestions.append(self._create_suggestion(current_suggestion))
                    current_suggestion = {}

            # 匹配位置
            pos_match = re.search(r"位置[：:]\s*(.+?)(?:[，,；;]|$)", line)
            if pos_match:
                current_suggestion["position"] = pos_match.group(1).strip()

            # 匹配描述
            desc_match = re.search(r"描述[：:]\s*(.+?)(?:[，,；;]|Prompt|prompt|$)", line, re.IGNORECASE)
            if desc_match:
                current_suggestion["description"] = desc_match.group(1).strip()

            # 匹配Prompt
            prompt_match = re.search(r"[Pp]rompt[：:]\s*(.+?)(?:[，,；;]|$)", line)
            if prompt_match:
                current_suggestion["prompt"] = prompt_match.group(1).strip()

            # 匹配类型
            if "论文原图" in line or "paper_figure" in line.lower():
                current_suggestion["type"] = "paper_figure"
            elif "AI生成" in line or "ai_generated" in line.lower() or "生成" in line:
                current_suggestion["type"] = "ai_generated"

            # 如果行中包含完整的描述/prompt信息（简化格式）
            if not current_suggestion.get("description") and not any(k in line for k in ["位置", "描述", "Prompt"]):
                # 可能是简化格式，整行作为描述
                cleaned = re.sub(r"^(\d+[.、)]|[-*•])\s*", "", line).strip()
                if cleaned and len(cleaned) > 10:
                    current_suggestion["description"] = cleaned

        # 处理最后一个
        if current_suggestion and current_suggestion.get("description"):
            suggestions.append(self._create_suggestion(current_suggestion))

        return suggestions

    def _create_suggestion(self, data: dict) -> ImageSuggestion:
        """创建配图建议对象"""
        return ImageSuggestion(
            position=0,  # 需要后续处理
            type=data.get("type", "ai_generated"),
            description=data.get("description", ""),
            prompt=data.get("prompt", data.get("description", "")),
            paper_figure_index=data.get("figure_index"),
        )


if __name__ == "__main__":
    # 测试需要先有初稿
    pass
