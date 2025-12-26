"""
论文图表提取模块
- 从PDF中截取指定区域的图表
- 高质量渲染输出
"""

from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

from ..parser.pdf_parser import Figure, PaperContent


class FigureExtractor:
    """论文图表提取器"""

    def __init__(self, output_dir: Path | str = "./output/figures"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_figure(
        self,
        pdf_path: Path,
        page_num: int,
        bbox: tuple[float, float, float, float] | None = None,
        output_name: str | None = None,
        dpi: int = 200,
    ) -> Path:
        """
        从PDF中截取指定区域

        Args:
            pdf_path: PDF文件路径
            page_num: 页码（从1开始）
            bbox: 截取区域 (x0, y0, x1, y1)，None表示整页
            output_name: 输出文件名
            dpi: 输出分辨率

        Returns:
            截取图片的路径
        """
        doc = fitz.open(pdf_path)
        page = doc[page_num - 1]

        # 设置缩放比例
        zoom = dpi / 72  # 72是PDF默认DPI
        mat = fitz.Matrix(zoom, zoom)

        if bbox:
            # 截取指定区域
            clip = fitz.Rect(bbox)
            pix = page.get_pixmap(matrix=mat, clip=clip)
        else:
            # 整页截取
            pix = page.get_pixmap(matrix=mat)

        # 保存图片
        if output_name is None:
            output_name = f"page_{page_num}.png"

        output_path = self.output_dir / output_name
        pix.save(str(output_path))

        doc.close()

        return output_path

    def extract_all_figures(
        self,
        paper: PaperContent,
        dpi: int = 200,
    ) -> list[tuple[Figure, Path]]:
        """
        提取论文中所有已识别的图表

        Args:
            paper: 解析后的论文内容
            dpi: 输出分辨率

        Returns:
            (Figure, 图片路径) 列表
        """
        results = []

        for figure in paper.figures:
            # 如果已有提取的图片，直接使用
            if figure.image_path and figure.image_path.exists():
                results.append((figure, figure.image_path))
                continue

            # 否则重新截取
            try:
                output_name = f"fig_p{figure.page_num}_{figure.index}.png"

                # 如果有bbox就用bbox，否则截取整页
                bbox = figure.bbox if any(figure.bbox) else None

                path = self.extract_figure(
                    pdf_path=paper.pdf_path,
                    page_num=figure.page_num,
                    bbox=bbox,
                    output_name=output_name,
                    dpi=dpi,
                )
                results.append((figure, path))

            except Exception as e:
                print(f"⚠️ 提取图表失败 (Figure {figure.index}): {e}")

        return results

    def extract_page_region(
        self,
        pdf_path: Path,
        page_num: int,
        region: str = "top",  # "top", "middle", "bottom", "left", "right"
        ratio: float = 0.5,
        dpi: int = 200,
    ) -> Path:
        """
        截取页面的指定区域

        Args:
            pdf_path: PDF文件路径
            page_num: 页码
            region: 区域 ("top", "middle", "bottom", "left", "right")
            ratio: 截取比例
            dpi: 分辨率

        Returns:
            图片路径
        """
        doc = fitz.open(pdf_path)
        page = doc[page_num - 1]
        rect = page.rect

        x0, y0, x1, y1 = rect

        if region == "top":
            y1 = y0 + (y1 - y0) * ratio
        elif region == "bottom":
            y0 = y1 - (y1 - y0) * ratio
        elif region == "middle":
            height = y1 - y0
            margin = height * (1 - ratio) / 2
            y0 += margin
            y1 -= margin
        elif region == "left":
            x1 = x0 + (x1 - x0) * ratio
        elif region == "right":
            x0 = x1 - (x1 - x0) * ratio

        bbox = (x0, y0, x1, y1)
        output_name = f"page_{page_num}_{region}.png"

        doc.close()

        return self.extract_figure(pdf_path, page_num, bbox, output_name, dpi)

    def create_figure_collage(
        self,
        figures: list[Path],
        output_name: str = "collage.png",
        max_width: int = 1200,
        padding: int = 20,
    ) -> Path:
        """
        将多个图表拼接成一张图

        Args:
            figures: 图片路径列表
            output_name: 输出文件名
            max_width: 最大宽度
            padding: 图片间距

        Returns:
            拼接图路径
        """
        if not figures:
            raise ValueError("没有图片可以拼接")

        # 加载所有图片
        images = [Image.open(f) for f in figures]

        # 计算目标尺寸
        # 简单实现：垂直排列
        total_height = sum(img.height for img in images) + padding * (len(images) - 1)
        max_img_width = max(img.width for img in images)
        target_width = min(max_img_width, max_width)

        # 缩放图片
        scaled_images = []
        scaled_height = 0

        for img in images:
            if img.width > target_width:
                ratio = target_width / img.width
                new_size = (target_width, int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            scaled_images.append(img)
            scaled_height += img.height

        scaled_height += padding * (len(scaled_images) - 1)

        # 创建画布
        collage = Image.new("RGB", (target_width, scaled_height), "white")

        # 粘贴图片
        y_offset = 0
        for img in scaled_images:
            # 居中
            x_offset = (target_width - img.width) // 2
            collage.paste(img, (x_offset, y_offset))
            y_offset += img.height + padding

        # 保存
        output_path = self.output_dir / output_name
        collage.save(output_path, quality=95)

        # 清理
        for img in images:
            img.close()

        return output_path


if __name__ == "__main__":
    # 测试
    extractor = FigureExtractor()

    # 需要一个测试PDF
    test_pdf = Path("./output/arxiv_1706.03762.pdf")
    if test_pdf.exists():
        # 截取第一页
        path = extractor.extract_figure(test_pdf, 1, output_name="test_page1.png")
        print(f"截取成功: {path}")
