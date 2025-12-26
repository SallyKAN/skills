"""
论文解析模块
- 下载PDF
- 提取文本内容
- 提取图表并截图保存
"""

import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import fitz  # PyMuPDF
import httpx
from PIL import Image


@dataclass
class Figure:
    """论文中的图表"""
    page_num: int
    index: int
    bbox: tuple[float, float, float, float]  # x0, y0, x1, y1
    caption: str = ""
    image_path: Path | None = None


@dataclass
class PaperContent:
    """解析后的论文内容"""
    title: str
    authors: list[str]
    abstract: str
    sections: dict[str, str]  # section_title -> content
    figures: list[Figure]
    references: list[str]
    full_text: str
    pdf_path: Path
    metadata: dict = field(default_factory=dict)


class PaperParser:
    """论文解析器"""

    def __init__(self, output_dir: Path | str = "./output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figures_dir = self.output_dir / "figures"
        self.figures_dir.mkdir(exist_ok=True)

    def parse(self, url: str) -> PaperContent:
        """
        解析论文URL，返回结构化内容

        支持:
        - arXiv链接 (abs/pdf)
        - 直接PDF链接
        """
        pdf_path = self._download_pdf(url)
        return self._parse_pdf(pdf_path)

    def _download_pdf(self, url: str) -> Path:
        """下载PDF文件"""
        # 处理arXiv链接
        if "arxiv.org" in url:
            url = self._normalize_arxiv_url(url)

        print(f"📥 下载论文: {url}")

        with httpx.Client(follow_redirects=True, timeout=60.0) as client:
            response = client.get(url)
            response.raise_for_status()

        # 保存PDF
        filename = self._extract_filename(url)
        pdf_path = self.output_dir / filename
        pdf_path.write_bytes(response.content)

        print(f"✅ PDF已保存: {pdf_path}")
        return pdf_path

    def _normalize_arxiv_url(self, url: str) -> str:
        """将arXiv链接转换为PDF下载链接"""
        # https://arxiv.org/abs/1706.03762 -> https://arxiv.org/pdf/1706.03762.pdf
        # https://arxiv.org/pdf/1706.03762 -> https://arxiv.org/pdf/1706.03762.pdf

        if "/abs/" in url:
            url = url.replace("/abs/", "/pdf/")

        if not url.endswith(".pdf"):
            url = url + ".pdf"

        return url

    def _extract_filename(self, url: str) -> str:
        """从URL提取文件名"""
        parsed = urlparse(url)
        path = parsed.path

        # arXiv格式: /pdf/1706.03762.pdf
        if "arxiv.org" in url:
            match = re.search(r"(\d+\.\d+)", path)
            if match:
                return f"arxiv_{match.group(1)}.pdf"

        # 其他情况
        filename = Path(path).name
        if not filename.endswith(".pdf"):
            filename = "paper.pdf"

        return filename

    def _parse_pdf(self, pdf_path: Path) -> PaperContent:
        """解析PDF文件"""
        print(f"📄 解析PDF: {pdf_path}")

        doc = fitz.open(pdf_path)

        # 提取元信息
        metadata = doc.metadata

        # 提取全文
        full_text = ""
        for page in doc:
            full_text += page.get_text()

        # 提取结构化内容
        title = self._extract_title(doc, metadata)
        authors = self._extract_authors(doc, full_text)
        abstract = self._extract_abstract(full_text)
        sections = self._extract_sections(full_text)
        figures = self._extract_figures(doc, pdf_path)
        references = self._extract_references(full_text)

        doc.close()

        print(f"✅ 解析完成: {title}")
        print(f"   - 作者: {len(authors)}人")
        print(f"   - 章节: {len(sections)}个")
        print(f"   - 图表: {len(figures)}个")

        return PaperContent(
            title=title,
            authors=authors,
            abstract=abstract,
            sections=sections,
            figures=figures,
            references=references,
            full_text=full_text,
            pdf_path=pdf_path,
            metadata=dict(metadata) if metadata else {},
        )

    def _extract_title(self, doc: fitz.Document, metadata: dict) -> str:
        """提取论文标题"""
        # 优先使用元数据
        if metadata and metadata.get("title"):
            return metadata["title"]

        # 从第一页提取（通常是最大字体的文本）
        first_page = doc[0]
        blocks = first_page.get_text("dict")["blocks"]

        max_size = 0
        title = ""

        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        if span["size"] > max_size:
                            max_size = span["size"]
                            title = span["text"]

        return title.strip() or "Unknown Title"

    def _extract_authors(self, doc: fitz.Document, full_text: str) -> list[str]:
        """提取作者列表"""
        # 简单实现：从第一页提取
        # 实际场景可能需要更复杂的NER或规则

        first_page_text = doc[0].get_text()
        lines = first_page_text.split("\n")

        authors = []
        in_author_section = False

        for line in lines[:30]:  # 只看前30行
            line = line.strip()

            # 跳过标题（通常是大写或很长）
            if len(line) > 100:
                continue

            # 检测作者区域（通常在标题后，摘要前）
            if "abstract" in line.lower():
                break

            # 简单的人名检测（包含逗号分隔的名字）
            if "," in line and len(line) < 200:
                # 可能是作者列表
                names = [n.strip() for n in line.split(",")]
                for name in names:
                    # 过滤明显不是人名的
                    if name and len(name) > 2 and not any(c.isdigit() for c in name):
                        if "@" not in name and "university" not in name.lower():
                            authors.append(name)

        return authors[:20]  # 最多返回20个作者

    def _extract_abstract(self, full_text: str) -> str:
        """提取摘要"""
        # 查找Abstract部分
        patterns = [
            r"Abstract[\s\n]+(.+?)(?=\n\s*\n|\n1[\.\s]|Introduction)",
            r"ABSTRACT[\s\n]+(.+?)(?=\n\s*\n|\n1[\.\s]|INTRODUCTION)",
        ]

        for pattern in patterns:
            match = re.search(pattern, full_text, re.DOTALL | re.IGNORECASE)
            if match:
                abstract = match.group(1).strip()
                # 清理换行
                abstract = re.sub(r"\s+", " ", abstract)
                return abstract[:2000]  # 限制长度

        return ""

    def _extract_sections(self, full_text: str) -> dict[str, str]:
        """提取章节内容"""
        sections = {}

        # 匹配章节标题模式：1. Introduction 或 1 Introduction 或 ## Introduction
        section_pattern = r"\n(\d+\.?\s+[A-Z][^\n]{3,50})\n"

        matches = list(re.finditer(section_pattern, full_text))

        for i, match in enumerate(matches):
            title = match.group(1).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)

            content = full_text[start:end].strip()
            # 清理内容
            content = re.sub(r"\s+", " ", content)

            sections[title] = content[:5000]  # 限制每个章节长度

        return sections

    def _extract_figures(self, doc: fitz.Document, pdf_path: Path) -> list[Figure]:
        """提取图表并保存为图片"""
        figures = []

        for page_num, page in enumerate(doc):
            # 获取页面上的图片
            image_list = page.get_images()

            for img_index, img in enumerate(image_list):
                xref = img[0]

                try:
                    # 提取图片
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    # 保存图片
                    img_filename = f"fig_p{page_num + 1}_{img_index + 1}.{image_ext}"
                    img_path = self.figures_dir / img_filename
                    img_path.write_bytes(image_bytes)

                    # 获取图片在页面上的位置
                    img_rect = page.get_image_rects(xref)
                    bbox = img_rect[0] if img_rect else (0, 0, 0, 0)

                    figure = Figure(
                        page_num=page_num + 1,
                        index=img_index + 1,
                        bbox=tuple(bbox),
                        image_path=img_path,
                    )
                    figures.append(figure)

                except Exception as e:
                    print(f"⚠️ 提取图片失败 (page {page_num + 1}, img {img_index + 1}): {e}")

        # 尝试匹配图片说明文字
        self._match_figure_captions(doc, figures)

        return figures

    def _match_figure_captions(self, doc: fitz.Document, figures: list[Figure]):
        """匹配图片说明文字"""
        for figure in figures:
            page = doc[figure.page_num - 1]
            text = page.get_text()

            # 查找Figure X或Fig. X格式的说明
            pattern = rf"(?:Figure|Fig\.?)\s*{figure.index}[\.:]\s*([^\n]+)"
            match = re.search(pattern, text, re.IGNORECASE)

            if match:
                figure.caption = match.group(1).strip()

    def _extract_references(self, full_text: str) -> list[str]:
        """提取参考文献"""
        references = []

        # 找到References部分
        ref_match = re.search(r"References?\s*\n", full_text, re.IGNORECASE)
        if not ref_match:
            return references

        ref_text = full_text[ref_match.end():]

        # 匹配编号的参考文献
        ref_pattern = r"\[(\d+)\]\s*([^\[]+)"
        matches = re.findall(ref_pattern, ref_text)

        for num, content in matches[:50]:  # 最多50条
            ref = content.strip()
            ref = re.sub(r"\s+", " ", ref)
            references.append(f"[{num}] {ref}")

        return references


# 便捷函数
def parse_paper(url: str, output_dir: str = "./output") -> PaperContent:
    """解析论文的便捷函数"""
    parser = PaperParser(output_dir=output_dir)
    return parser.parse(url)


if __name__ == "__main__":
    # 测试
    import sys

    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        # 默认测试：Attention Is All You Need
        url = "https://arxiv.org/abs/1706.03762"

    content = parse_paper(url)
    print(f"\n{'='*50}")
    print(f"标题: {content.title}")
    print(f"作者: {', '.join(content.authors[:5])}...")
    print(f"摘要: {content.abstract[:200]}...")
