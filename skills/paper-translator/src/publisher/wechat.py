"""
微信公众号发布模块
- 获取access_token
- 上传素材（图片）
- 创建草稿
- Markdown转HTML
"""

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
import markdown
from bs4 import BeautifulSoup


@dataclass
class WeChatConfig:
    """微信公众号配置"""
    app_id: str
    app_secret: str


@dataclass
class DraftArticle:
    """草稿文章"""
    title: str
    content: str  # HTML内容
    thumb_media_id: str  # 封面图media_id
    author: str = ""
    digest: str = ""  # 摘要
    content_source_url: str = ""  # 原文链接
    need_open_comment: int = 0  # 是否打开评论
    only_fans_can_comment: int = 0  # 是否仅粉丝可评论


@dataclass
class PublishResult:
    """发布结果"""
    success: bool
    media_id: str | None = None  # 草稿media_id
    error: str | None = None


class WeChatPublisher:
    """微信公众号发布器"""

    BASE_URL = "https://api.weixin.qq.com/cgi-bin"

    def __init__(
        self,
        app_id: str | None = None,
        app_secret: str | None = None,
    ):
        self.app_id = app_id or os.getenv("WECHAT_APP_ID")
        self.app_secret = app_secret or os.getenv("WECHAT_APP_SECRET")

        if not self.app_id or not self.app_secret:
            raise ValueError("请设置WECHAT_APP_ID和WECHAT_APP_SECRET环境变量")

        self._access_token: str | None = None
        self._token_expires: float = 0

        self.client = httpx.Client(timeout=30.0)

    def __del__(self):
        if hasattr(self, "client"):
            self.client.close()

    @property
    def access_token(self) -> str:
        """获取access_token（自动缓存和刷新）"""
        if self._access_token and time.time() < self._token_expires:
            return self._access_token

        url = f"{self.BASE_URL}/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.app_id,
            "secret": self.app_secret,
        }

        response = self.client.get(url, params=params)
        data = response.json()

        if "access_token" not in data:
            raise Exception(f"获取access_token失败: {data}")

        self._access_token = data["access_token"]
        # 提前5分钟过期
        self._token_expires = time.time() + data.get("expires_in", 7200) - 300

        return self._access_token

    def upload_image(self, image_path: Path | str) -> str:
        """
        上传图片到微信素材库

        Args:
            image_path: 图片路径

        Returns:
            media_id
        """
        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(f"图片不存在: {image_path}")

        url = f"{self.BASE_URL}/media/uploadimg"
        params = {"access_token": self.access_token}

        with open(image_path, "rb") as f:
            files = {"media": (image_path.name, f, "image/png")}
            response = self.client.post(url, params=params, files=files)

        data = response.json()

        if "url" not in data:
            raise Exception(f"上传图片失败: {data}")

        return data["url"]

    def upload_thumb(self, image_path: Path | str) -> str:
        """
        上传封面图（永久素材）

        Args:
            image_path: 图片路径

        Returns:
            media_id
        """
        image_path = Path(image_path)

        url = f"{self.BASE_URL}/material/add_material"
        params = {
            "access_token": self.access_token,
            "type": "image",
        }

        with open(image_path, "rb") as f:
            files = {"media": (image_path.name, f, "image/png")}
            response = self.client.post(url, params=params, files=files)

        data = response.json()

        if "media_id" not in data:
            raise Exception(f"上传封面图失败: {data}")

        return data["media_id"]

    def create_draft(self, article: DraftArticle) -> PublishResult:
        """
        创建草稿

        Args:
            article: 草稿文章

        Returns:
            发布结果
        """
        url = f"{self.BASE_URL}/draft/add"
        params = {"access_token": self.access_token}

        data = {
            "articles": [
                {
                    "title": article.title,
                    "author": article.author,
                    "digest": article.digest or article.title[:50],
                    "content": article.content,
                    "content_source_url": article.content_source_url,
                    "thumb_media_id": article.thumb_media_id,
                    "need_open_comment": article.need_open_comment,
                    "only_fans_can_comment": article.only_fans_can_comment,
                }
            ]
        }

        response = self.client.post(url, params=params, json=data)
        result = response.json()

        if "media_id" in result:
            return PublishResult(success=True, media_id=result["media_id"])
        else:
            return PublishResult(
                success=False,
                error=result.get("errmsg", str(result)),
            )

    def markdown_to_wechat_html(
        self,
        md_content: str,
        upload_images: bool = True,
        style: str = "default",
    ) -> str:
        """
        将Markdown转换为微信公众号兼容的HTML

        Args:
            md_content: Markdown内容
            upload_images: 是否上传本地图片到微信
            style: 样式主题

        Returns:
            微信兼容的HTML
        """
        # Markdown转HTML
        html = markdown.markdown(
            md_content,
            extensions=[
                "extra",
                "codehilite",
                "tables",
                "toc",
            ],
        )

        # 解析HTML
        soup = BeautifulSoup(html, "html.parser")

        # 处理图片
        if upload_images:
            for img in soup.find_all("img"):
                src = img.get("src", "")
                if src and not src.startswith("http"):
                    # 本地图片，上传到微信
                    try:
                        wechat_url = self.upload_image(src)
                        img["src"] = wechat_url
                    except Exception as e:
                        print(f"⚠️ 上传图片失败: {e}")

        # 应用微信样式
        styled_html = self._apply_wechat_style(soup, style)

        return styled_html

    def _apply_wechat_style(self, soup: BeautifulSoup, style: str) -> str:
        """应用微信公众号样式"""
        # 基础样式
        styles = {
            "default": {
                "body": "font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; font-size: 16px; line-height: 1.8; color: #333;",
                "h1": "font-size: 24px; font-weight: bold; margin: 20px 0 15px; color: #1a1a1a;",
                "h2": "font-size: 20px; font-weight: bold; margin: 18px 0 12px; color: #1a1a1a; border-bottom: 1px solid #eee; padding-bottom: 8px;",
                "h3": "font-size: 18px; font-weight: bold; margin: 15px 0 10px; color: #333;",
                "p": "margin: 15px 0; text-align: justify;",
                "code": "background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-family: Consolas, Monaco, monospace; font-size: 14px; color: #c7254e;",
                "pre": "background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; font-size: 14px;",
                "blockquote": "border-left: 4px solid #ddd; padding: 10px 15px; margin: 15px 0; background: #f9f9f9; color: #666;",
                "img": "max-width: 100%; height: auto; display: block; margin: 15px auto;",
                "strong": "font-weight: bold; color: #1a1a1a;",
                "a": "color: #576b95; text-decoration: none;",
                "ul": "margin: 15px 0; padding-left: 25px;",
                "ol": "margin: 15px 0; padding-left: 25px;",
                "li": "margin: 8px 0;",
                "table": "border-collapse: collapse; width: 100%; margin: 15px 0;",
                "th": "border: 1px solid #ddd; padding: 10px; background: #f5f5f5; font-weight: bold;",
                "td": "border: 1px solid #ddd; padding: 10px;",
            }
        }

        style_dict = styles.get(style, styles["default"])

        # 为每个标签添加内联样式（微信不支持外部CSS）
        for tag, css in style_dict.items():
            if tag == "body":
                continue
            for element in soup.find_all(tag):
                existing_style = element.get("style", "")
                element["style"] = f"{css} {existing_style}".strip()

        # 包装在section中
        body_style = style_dict.get("body", "")
        wrapped = f'<section style="{body_style}">{str(soup)}</section>'

        return wrapped

    def publish_article(
        self,
        title: str,
        md_content: str,
        cover_image: Path | str,
        author: str = "",
        source_url: str = "",
    ) -> PublishResult:
        """
        发布文章到草稿箱（一键发布）

        Args:
            title: 文章标题
            md_content: Markdown内容
            cover_image: 封面图路径
            author: 作者
            source_url: 原文链接

        Returns:
            发布结果
        """
        print(f"📤 正在发布文章到公众号草稿...")
        print(f"   标题: {title}")

        # 1. 上传封面图
        print("   上传封面图...")
        thumb_media_id = self.upload_thumb(cover_image)

        # 2. 转换Markdown为HTML
        print("   转换HTML...")
        html_content = self.markdown_to_wechat_html(md_content)

        # 3. 创建草稿
        print("   创建草稿...")
        article = DraftArticle(
            title=title,
            content=html_content,
            thumb_media_id=thumb_media_id,
            author=author,
            content_source_url=source_url,
        )

        result = self.create_draft(article)

        if result.success:
            print(f"✅ 发布成功！草稿media_id: {result.media_id}")
        else:
            print(f"❌ 发布失败: {result.error}")

        return result


# 便捷函数
def publish_to_wechat(
    title: str,
    md_content: str,
    cover_image: str,
    author: str = "",
) -> PublishResult:
    """发布文章到微信公众号草稿"""
    publisher = WeChatPublisher()
    return publisher.publish_article(title, md_content, cover_image, author)


if __name__ == "__main__":
    # 测试（需要配置环境变量）
    publisher = WeChatPublisher()

    # 测试获取token
    try:
        token = publisher.access_token
        print(f"获取token成功: {token[:20]}...")
    except Exception as e:
        print(f"获取token失败: {e}")
