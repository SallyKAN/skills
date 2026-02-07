---
name: wechat-publisher
description: Use when publishing Markdown content to WeChat Official Account, uploading images to WeChat, or creating WeChat drafts. Triggers include "发布到微信公众号", "上传到公众号", "创建微信草稿".
---

# WeChat Publisher

将 Markdown 内容发布到微信公众号草稿箱的通用模块。

## 功能

- **Markdown 转 HTML** - 自动转换为微信公众号兼容的 HTML（内联 CSS）
- **图片上传** - 自动上传本地图片到微信素材库
- **封面图管理** - 上传并设置文章封面
- **草稿创建** - 将文章发布到微信公众号草稿箱

## 前置条件

1. **环境变量**:
   ```bash
   WECHAT_APP_ID=your_app_id
   WECHAT_APP_SECRET=your_app_secret
   ```

2. **依赖安装**:
   ```bash
   cd ~/skills/skills/wechat-publisher
   pip install -r requirements.txt
   ```

3. **代理问题**（重要）:
   ```python
   import os
   # 清除代理环境变量（在调用微信 API 前必须执行）
   for var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY']:
       os.environ.pop(var, None)
   ```

## 快速使用

```python
import os
# 1. 清除代理
for var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY']:
    os.environ.pop(var, None)

# 2. 导入并使用
from src.publisher import WeChatPublisher

publisher = WeChatPublisher()
result = publisher.publish_article(
    title="文章标题",
    md_content="# 标题\n\n内容...",
    cover_image="cover.png",
    author="作者名",
    source_url="https://原文链接",  # 可选
)

if result.success:
    print(f"发布成功！草稿 ID: {result.media_id}")
```

## API 参考

| 方法 | 描述 |
|------|------|
| `publish_article(title, md_content, cover_image, author, source_url)` | 一键发布（推荐） |
| `upload_image(image_path)` | 上传正文图片，返回微信 URL |
| `upload_thumb(image_path)` | 上传封面图，返回 media_id |
| `markdown_to_wechat_html(md_content, upload_images, style)` | Markdown 转微信 HTML |
| `create_draft(article)` | 创建草稿 |

## 数据类

```python
@dataclass
class DraftArticle:
    title: str
    content: str           # HTML 内容
    thumb_media_id: str    # 封面图 media_id
    author: str = ""
    digest: str = ""       # 摘要（默认取标题前50字）
    content_source_url: str = ""
    need_open_comment: int = 0
    only_fans_can_comment: int = 0

@dataclass
class PublishResult:
    success: bool
    media_id: str | None = None
    error: str | None = None
```

## 常见错误

| 错误 | 解决方案 |
|------|----------|
| `Unknown scheme for proxy URL` | 清除代理环境变量 |
| `请设置WECHAT_APP_ID` | 设置环境变量 |
| 图片上传失败 | 检查图片 < 2MB，格式为 PNG/JPG/GIF |

## 注意事项

- 图片大小 < 2MB
- 草稿 API 有频率限制
- 需要认证的服务号或订阅号
- Access Token 自动缓存和刷新（提前5分钟）
