---
name: wechat-article-writer
description: Use when converting content (tweets, blogs, tutorials) into WeChat Official Account articles. Triggers include "把这篇转成微信公众号文章", "帮我写一篇微信公众号", "发布到公众号".
---

# WeChat Article Writer

将任何内容源（推特、博客、论文等）转化为精美的微信公众号文章。

## 依赖

- `wechat-publisher` - 微信发布
- `image-generator` - AI 配图生成

## 工作流程

### 1. 内容获取

```python
# URL 内容
content = WebFetch(url="https://...", prompt="提取完整内容")
# 或用户提供的文本
content = user_provided_text
```

### 2. 文章创作

**写作原则**:
- 去机翻腔，使用自然流畅的中文
- 口语化表达，有温度
- 结构清晰，使用小标题
- 平衡专业性和可读性

**文章结构**:
```markdown
# [吸引眼球的标题]

[引子段落]

---

## 第一个要点
[自然的叙述]

---

## 总结/写在最后
[收尾，引发思考]

---
*原文链接: [source]*
```

### 3. 配图生成

```python
import os
os.environ['OPENROUTER_API_KEY'] = 'your_key'

# 清除代理
for var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY']:
    os.environ.pop(var, None)

from image_generator.src.generator import ImageGenerator

generator = ImageGenerator(output_dir="./output/images")

# 封面图
cover = generator.generate_cover(title="文章标题", style="chalkboard")

# 内容配图
img = generator.generate(prompt="配图描述")
```

### 4. 发布到微信

```python
from wechat_publisher.src.publisher import WeChatPublisher

publisher = WeChatPublisher()
result = publisher.publish_article(
    title="文章标题",
    md_content=content,
    cover_image="output/images/cover.png",
    author="作者名",
)
```

## 最佳实践

### 内容创作
- **标题**: 12-25字，包含数字或强烈对比
- **开篇**: 直接点题，引发好奇
- **结构**: 3-6个大章节
- **语言**: 70%口语化 + 30%专业术语
- **长度**: 1500-3000字

### 配图策略
- **封面**: 必须有，黑板报风格辨识度高
- **数量**: 2-4张，不宜过多
- **位置**: 重要概念、对比、流程图处

## 注意事项

1. 发布前**必须**清除代理环境变量
2. 图片大小 < 2MB
3. 在微信后台最终调整格式再发布
