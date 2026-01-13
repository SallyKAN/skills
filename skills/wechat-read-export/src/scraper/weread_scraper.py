"""
微信读书数据抓取模块

从微信读书网页版抓取书架和笔记数据
"""

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from playwright.sync_api import BrowserContext, Page

from .auth import AuthManager


@dataclass
class Highlight:
    """划线/高亮"""

    content: str
    chapter: str = ""
    chapter_uid: int = 0
    create_time: int = 0
    style: int = 0  # 划线样式

    @property
    def created_at(self) -> datetime:
        return datetime.fromtimestamp(self.create_time) if self.create_time else None


@dataclass
class Thought:
    """想法/笔记"""

    content: str
    abstract: str = ""  # 关联的原文
    chapter: str = ""
    create_time: int = 0

    @property
    def created_at(self) -> datetime:
        return datetime.fromtimestamp(self.create_time) if self.create_time else None


@dataclass
class BookInfo:
    """书籍信息"""

    book_id: str
    title: str
    author: str = ""
    cover: str = ""
    category: str = ""
    intro: str = ""
    publisher: str = ""
    publish_time: str = ""


@dataclass
class BookNotes:
    """书籍笔记"""

    book: BookInfo
    highlights: list[Highlight] = field(default_factory=list)
    thoughts: list[Thought] = field(default_factory=list)
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def total_notes(self) -> int:
        return len(self.highlights) + len(self.thoughts)


class WeReadScraper:
    """微信读书数据抓取器"""

    WEREAD_URL = "https://weread.qq.com"
    SHELF_URL = "https://weread.qq.com/web/shelf"
    READER_URL = "https://weread.qq.com/web/reader/{book_id}"
    # API 使用数字格式的 book_id
    NOTES_API = "https://weread.qq.com/web/book/bookmarklist?bookId={book_id}&syncKey=0"
    REVIEW_API = "https://weread.qq.com/web/review/list?bookId={book_id}&listType=11&listMode=3&syncKey=0&mine=1"

    DEFAULT_DATA_DIR = Path.home() / ".wechat-read-export" / "data"

    def __init__(
        self,
        auth_manager: AuthManager | None = None,
        data_dir: Path | None = None,
    ):
        self.auth_manager = auth_manager or AuthManager()
        self.data_dir = data_dir or self.DEFAULT_DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._captured_api_data: dict = {}  # 存储拦截到的 API 数据

    def _ensure_context(self, headless: bool = False) -> BrowserContext:
        """确保有已认证的浏览器上下文"""
        if self._context is None:
            self._context, _ = self.auth_manager.get_authenticated_context(
                headless=headless
            )
        return self._context

    def _get_page(self) -> Page:
        """获取页面实例"""
        if self._page is None or self._page.is_closed():
            context = self._ensure_context()
            self._page = context.new_page()
            # 设置 API 响应拦截
            self._page.on("response", self._handle_response)
        return self._page

    def _handle_response(self, response) -> None:
        """拦截并存储 API 响应"""
        url = response.url
        if "weread.qq.com" not in url:
            return

        content_type = response.headers.get("content-type", "")
        if "json" not in content_type:
            return

        try:
            data = response.json()
            # 存储书签列表 API 响应
            if "bookmarklist" in url:
                self._captured_api_data["bookmarks"] = data
            # 存储评论/想法 API 响应
            elif "review/list" in url and "mine=1" in url:
                self._captured_api_data["reviews"] = data
        except Exception:
            pass

    def _fetch_json(self, url: str) -> dict:
        """通过页面获取 JSON 数据"""
        page = self._get_page()
        response = page.goto(url)
        if response and response.ok:
            try:
                data = response.json()
                return data
            except Exception as e:
                print(f"  JSON 解析失败: {e}")
                # 尝试获取页面文本内容
                text = page.content()
                print(f"  页面内容: {text[:500]}")
                return {}
        else:
            print(f"  请求失败: {response.status if response else 'No response'}")
        return {}

    def get_shelf_books(self) -> list[dict]:
        """获取书架上的所有书籍"""
        print("正在获取书架信息...")
        page = self._get_page()
        page.goto(self.SHELF_URL)
        page.wait_for_load_state("networkidle")

        # 等待书架列表出现
        try:
            page.wait_for_selector(".shelf_list", timeout=10000)
        except Exception:
            print("警告: 未找到书架列表，可能需要重新登录")

        # 等待书籍元素出现
        try:
            page.wait_for_selector(".shelfBook", timeout=10000)
        except Exception:
            print("警告: 未找到书籍元素")

        # 滚动加载所有书籍
        books = []
        last_count = 0
        max_scroll = 20

        for i in range(max_scroll):
            # 获取当前页面的书籍（使用新的选择器 .shelfBook）
            book_elements = page.query_selector_all(".shelfBook")
            current_count = len(book_elements)

            if current_count > 0 and current_count == last_count:
                break

            last_count = current_count
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(0.5)

        # 提取书籍信息
        book_elements = page.query_selector_all(".shelfBook")
        print(f"找到 {len(book_elements)} 个书籍元素")

        for elem in book_elements:
            # 从 href 中提取 book_id，格式: /web/reader/{book_id}
            href = elem.get_attribute("href") or ""
            book_id = href.replace("/web/reader/", "") if "/web/reader/" in href else ""

            if book_id:
                title_elem = elem.query_selector(".title")
                cover_elem = elem.query_selector(".wr_bookCover_img")

                title = ""
                if title_elem:
                    title = title_elem.get_attribute("title") or title_elem.inner_text()

                books.append(
                    {
                        "book_id": book_id,
                        "title": title,
                        "author": "",  # 书架页面不显示作者，后续从详情获取
                        "cover": cover_elem.get_attribute("src") if cover_elem else "",
                    }
                )

        print(f"找到 {len(books)} 本书")
        return books

    def get_book_info(self, book_id: str, title: str = "", author: str = "", cover: str = "") -> BookInfo:
        """获取书籍详细信息"""
        # 从书架数据或 API 响应中获取
        book_data = self._captured_api_data.get("bookmarks", {}).get("book", {})
        return BookInfo(
            book_id=book_id,
            title=title or book_data.get("title", ""),
            author=author or book_data.get("author", ""),
            cover=cover or book_data.get("cover", ""),
            intro=book_data.get("intro", ""),
            publisher=book_data.get("publisher", ""),
        )

    def get_book_highlights_from_api(self) -> list[Highlight]:
        """从拦截的 API 数据中提取划线"""
        highlights = []
        bookmarks_data = self._captured_api_data.get("bookmarks", {})
        chapters = {c.get("chapterUid"): c.get("title", "") for c in bookmarks_data.get("chapters", [])}

        for item in bookmarks_data.get("updated", []):
            content = item.get("markText", "")
            if content:
                chapter_uid = item.get("chapterUid", 0)
                highlights.append(
                    Highlight(
                        content=content,
                        chapter=chapters.get(chapter_uid, ""),
                        chapter_uid=chapter_uid,
                        create_time=item.get("createTime", 0),
                        style=item.get("style", 0),
                    )
                )

        return highlights

    def get_book_thoughts_from_api(self) -> list[Thought]:
        """从拦截的 API 数据中提取想法"""
        thoughts = []
        reviews_data = self._captured_api_data.get("reviews", {})

        for item in reviews_data.get("reviews", []):
            review = item.get("review", {})
            content = review.get("content", "")
            if content:
                thoughts.append(
                    Thought(
                        content=content,
                        abstract=review.get("abstract", ""),
                        chapter=review.get("chapterTitle", ""),
                        create_time=review.get("createTime", 0),
                    )
                )

        return thoughts

    def scrape_book_by_reader_page(self, url_book_id: str, title: str = "", author: str = "", cover: str = "") -> BookNotes:
        """
        通过访问阅读器页面来抓取书籍笔记

        Args:
            url_book_id: URL 格式的 book_id（如 538320a0813ab83e4g01836b）
            title: 书名（可选，从书架获取）
            author: 作者（可选）
            cover: 封面 URL（可选）
        """
        print(f"正在抓取书籍笔记: {title or url_book_id}")

        # 清空之前的 API 数据
        self._captured_api_data = {}

        # 访问阅读器页面，触发 API 请求
        page = self._get_page()
        reader_url = self.READER_URL.format(book_id=url_book_id)
        page.goto(reader_url)
        page.wait_for_load_state("networkidle")
        time.sleep(2)  # 等待 API 响应被拦截

        # 从拦截的数据中提取笔记
        highlights = self.get_book_highlights_from_api()
        thoughts = self.get_book_thoughts_from_api()
        book_info = self.get_book_info(url_book_id, title, author, cover)

        print(f"  书名: {book_info.title}")
        print(f"  划线: {len(highlights)} 条")
        print(f"  想法: {len(thoughts)} 条")

        return BookNotes(
            book=book_info,
            highlights=highlights,
            thoughts=thoughts,
        )

    def scrape_all_books(self, book_filter: str | None = None) -> list[BookNotes]:
        """
        抓取所有书籍的笔记

        Args:
            book_filter: 书名过滤（包含此字符串的书籍）
        """
        shelf_books = self.get_shelf_books()

        if book_filter:
            shelf_books = [b for b in shelf_books if book_filter in b.get("title", "")]
            print(f"过滤后剩余 {len(shelf_books)} 本书")

        all_notes = []
        for book in shelf_books:
            book_id = book["book_id"]
            title = book.get("title", "")
            author = book.get("author", "")
            cover = book.get("cover", "")

            notes = self.scrape_book_by_reader_page(book_id, title, author, cover)
            if notes.total_notes > 0:
                all_notes.append(notes)
                self._save_book_notes(notes)

        return all_notes

    def _save_book_notes(self, notes: BookNotes) -> Path:
        """保存书籍笔记到本地"""
        filename = f"{notes.book.book_id}.json"
        filepath = self.data_dir / filename

        # 转换为可序列化的字典
        data = {
            "book": asdict(notes.book),
            "highlights": [asdict(h) for h in notes.highlights],
            "thoughts": [asdict(t) for t in notes.thoughts],
            "scraped_at": notes.scraped_at,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"  已保存到: {filepath}")
        return filepath

    def load_book_notes(self, book_id: str) -> BookNotes | None:
        """从本地加载书籍笔记"""
        filepath = self.data_dir / f"{book_id}.json"
        if not filepath.exists():
            return None

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        return BookNotes(
            book=BookInfo(**data["book"]),
            highlights=[Highlight(**h) for h in data["highlights"]],
            thoughts=[Thought(**t) for t in data["thoughts"]],
            scraped_at=data.get("scraped_at", ""),
        )

    def list_saved_books(self) -> list[dict]:
        """列出已保存的书籍"""
        books = []
        for filepath in self.data_dir.glob("*.json"):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                book = data.get("book", {})
                books.append(
                    {
                        "book_id": book.get("book_id"),
                        "title": book.get("title"),
                        "author": book.get("author"),
                        "highlights": len(data.get("highlights", [])),
                        "thoughts": len(data.get("thoughts", [])),
                        "scraped_at": data.get("scraped_at"),
                    }
                )
        return books

    def close(self):
        """关闭浏览器"""
        if self._page:
            self._page.close()
        if self._context:
            self._context.close()
