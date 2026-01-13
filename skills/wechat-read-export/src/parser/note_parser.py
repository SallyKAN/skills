"""
笔记解析模块

将抓取的原始数据解析为结构化格式
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json

from ..scraper.weread_scraper import BookNotes, BookInfo, Highlight, Thought


@dataclass
class ChapterNotes:
    """章节笔记"""

    chapter: str
    highlights: list[Highlight]
    thoughts: list[Thought]

    @property
    def total_notes(self) -> int:
        return len(self.highlights) + len(self.thoughts)


@dataclass
class ParsedBookNotes:
    """解析后的书籍笔记"""

    book: BookInfo
    chapters: list[ChapterNotes]
    all_highlights: list[Highlight]
    all_thoughts: list[Thought]
    scraped_at: str

    @property
    def total_highlights(self) -> int:
        return len(self.all_highlights)

    @property
    def total_thoughts(self) -> int:
        return len(self.all_thoughts)

    @property
    def total_notes(self) -> int:
        return self.total_highlights + self.total_thoughts


class NoteParser:
    """笔记解析器"""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or Path.home() / ".wechat-read-export" / "data"

    def parse(self, book_notes: BookNotes) -> ParsedBookNotes:
        """
        解析书籍笔记，按章节组织

        Args:
            book_notes: 原始书籍笔记数据

        Returns:
            解析后的书籍笔记
        """
        # 按章节分组
        chapter_map: dict[str, ChapterNotes] = {}

        # 处理划线
        for highlight in book_notes.highlights:
            chapter = highlight.chapter or "未分类"
            if chapter not in chapter_map:
                chapter_map[chapter] = ChapterNotes(
                    chapter=chapter, highlights=[], thoughts=[]
                )
            chapter_map[chapter].highlights.append(highlight)

        # 处理想法
        for thought in book_notes.thoughts:
            chapter = thought.chapter or "未分类"
            if chapter not in chapter_map:
                chapter_map[chapter] = ChapterNotes(
                    chapter=chapter, highlights=[], thoughts=[]
                )
            chapter_map[chapter].thoughts.append(thought)

        # 按章节顺序排序（使用第一条笔记的时间）
        chapters = list(chapter_map.values())
        chapters.sort(
            key=lambda c: min(
                [h.create_time for h in c.highlights] + [t.create_time for t in c.thoughts] + [float("inf")]
            )
        )

        return ParsedBookNotes(
            book=book_notes.book,
            chapters=chapters,
            all_highlights=book_notes.highlights,
            all_thoughts=book_notes.thoughts,
            scraped_at=book_notes.scraped_at,
        )

    def load_and_parse(self, book_id: str) -> ParsedBookNotes | None:
        """从本地加载并解析书籍笔记"""
        filepath = self.data_dir / f"{book_id}.json"
        if not filepath.exists():
            return None

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        book_notes = BookNotes(
            book=BookInfo(**data["book"]),
            highlights=[Highlight(**h) for h in data["highlights"]],
            thoughts=[Thought(**t) for t in data["thoughts"]],
            scraped_at=data.get("scraped_at", ""),
        )

        return self.parse(book_notes)

    def load_all_parsed(self) -> list[ParsedBookNotes]:
        """加载并解析所有已保存的书籍笔记"""
        parsed_books = []
        for filepath in self.data_dir.glob("*.json"):
            book_id = filepath.stem
            parsed = self.load_and_parse(book_id)
            if parsed:
                parsed_books.append(parsed)
        return parsed_books

    def get_all_highlights_text(self, parsed: ParsedBookNotes) -> str:
        """获取所有划线的纯文本（用于 AI 处理）"""
        texts = []
        for chapter in parsed.chapters:
            if chapter.highlights:
                texts.append(f"\n## {chapter.chapter}\n")
                for h in chapter.highlights:
                    texts.append(f"- {h.content}")
        return "\n".join(texts)

    def get_all_thoughts_text(self, parsed: ParsedBookNotes) -> str:
        """获取所有想法的纯文本（用于 AI 处理）"""
        texts = []
        for chapter in parsed.chapters:
            if chapter.thoughts:
                texts.append(f"\n## {chapter.chapter}\n")
                for t in chapter.thoughts:
                    if t.abstract:
                        texts.append(f"> {t.abstract}")
                    texts.append(f"想法: {t.content}\n")
        return "\n".join(texts)
