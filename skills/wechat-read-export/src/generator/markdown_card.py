"""
Markdown 知识卡片生成器

将解析后的笔记生成 Markdown 格式的知识卡片
"""

import os
from datetime import datetime
from pathlib import Path

from anthropic import Anthropic

from ..parser.note_parser import ParsedBookNotes, ChapterNotes


class MarkdownCardGenerator:
    """Markdown 知识卡片生成器"""

    PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

    def __init__(
        self,
        output_dir: Path | None = None,
        ai_provider: str = "anthropic",
        ai_model: str | None = None,
    ):
        self.output_dir = output_dir or Path("./output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.ai_provider = ai_provider
        self.ai_model = ai_model or "claude-sonnet-4-20250514"
        self._client = None

    def _get_ai_client(self):
        """获取 AI 客户端"""
        if self._client is None:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("请设置 ANTHROPIC_API_KEY 环境变量")
            self._client = Anthropic(api_key=api_key)
        return self._client

    def _load_prompt(self, name: str) -> str:
        """加载提示词模板"""
        prompt_file = self.PROMPTS_DIR / f"{name}.md"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
        return ""

    def _call_ai(self, prompt: str) -> str:
        """调用 AI 生成内容"""
        client = self._get_ai_client()
        response = client.messages.create(
            model=self.ai_model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def _generate_summary(self, parsed: ParsedBookNotes) -> str:
        """生成书籍核心观点总结"""
        prompt_template = self._load_prompt("summarize")
        if not prompt_template:
            return ""

        # 准备划线内容
        highlights_text = []
        for chapter in parsed.chapters:
            for h in chapter.highlights:
                highlights_text.append(f"- {h.content}")

        # 准备想法内容
        thoughts_text = []
        for chapter in parsed.chapters:
            for t in chapter.thoughts:
                if t.abstract:
                    thoughts_text.append(f"> {t.abstract}")
                thoughts_text.append(f"想法: {t.content}")

        # 填充模板
        prompt = prompt_template.replace("{{book_title}}", parsed.book.title)
        prompt = prompt.replace("{{author}}", parsed.book.author)
        prompt = prompt.replace("{{highlights}}", "\n".join(highlights_text))
        prompt = prompt.replace("{{thoughts}}", "\n".join(thoughts_text))

        try:
            return self._call_ai(prompt)
        except Exception as e:
            print(f"AI 生成失败: {e}")
            return ""

    def _format_chapter_notes(self, chapter: ChapterNotes) -> str:
        """格式化章节笔记"""
        lines = [f"\n### {chapter.chapter}\n"]

        for highlight in chapter.highlights:
            lines.append(f"> {highlight.content}\n")
            if highlight.created_at:
                lines.append(
                    f"*— 划线于 {highlight.created_at.strftime('%Y-%m-%d')}*\n"
                )

        for thought in chapter.thoughts:
            if thought.abstract:
                lines.append(f"> {thought.abstract}\n")
            lines.append(f"**我的想法**: {thought.content}\n")
            if thought.created_at:
                lines.append(
                    f"*— 记录于 {thought.created_at.strftime('%Y-%m-%d')}*\n"
                )

        return "\n".join(lines)

    def generate(self, parsed: ParsedBookNotes, with_ai: bool = True) -> str:
        """
        生成 Markdown 知识卡片

        Args:
            parsed: 解析后的书籍笔记
            with_ai: 是否使用 AI 生成总结

        Returns:
            Markdown 内容
        """
        book = parsed.book
        lines = []

        # 标题
        lines.append(f"# 《{book.title}》知识卡片\n")

        # 书籍信息
        lines.append("## 书籍信息\n")
        if book.cover:
            lines.append(f"![封面]({book.cover})\n")
        lines.append(f"- **书名**: {book.title}")
        lines.append(f"- **作者**: {book.author}")
        if book.publisher:
            lines.append(f"- **出版社**: {book.publisher}")
        lines.append(f"- **划线数量**: {parsed.total_highlights}")
        lines.append(f"- **想法数量**: {parsed.total_thoughts}")
        lines.append(f"- **导出时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

        # AI 生成的核心观点
        if with_ai and (parsed.total_highlights > 0 or parsed.total_thoughts > 0):
            print("正在生成 AI 总结...")
            summary = self._generate_summary(parsed)
            if summary:
                lines.append(summary)
                lines.append("")

        # 精华摘录
        lines.append("## 精华摘录\n")
        for chapter in parsed.chapters:
            if chapter.total_notes > 0:
                lines.append(self._format_chapter_notes(chapter))

        return "\n".join(lines)

    def generate_and_save(
        self, parsed: ParsedBookNotes, with_ai: bool = True
    ) -> Path:
        """生成并保存 Markdown 知识卡片"""
        content = self.generate(parsed, with_ai=with_ai)

        # 生成文件名（移除特殊字符）
        safe_title = "".join(
            c for c in parsed.book.title if c.isalnum() or c in " _-"
        ).strip()
        filename = f"{safe_title}_知识卡片.md"
        filepath = self.output_dir / filename

        filepath.write_text(content, encoding="utf-8")
        print(f"知识卡片已保存到: {filepath}")

        return filepath

    def generate_all(
        self, parsed_books: list[ParsedBookNotes], with_ai: bool = True
    ) -> list[Path]:
        """批量生成所有书籍的知识卡片"""
        paths = []
        for parsed in parsed_books:
            if parsed.total_notes > 0:
                path = self.generate_and_save(parsed, with_ai=with_ai)
                paths.append(path)
        return paths
