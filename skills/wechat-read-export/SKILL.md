---
name: wechat-read-export
description: 自动导出微信读书笔记并通过 AI 整理成知识卡片。当用户想要导出微信读书笔记、整理读书笔记、生成知识卡片、或者说"帮我整理微信读书的笔记"时使用此技能。
allowed-tools: Bash,Read,Write,Edit,Glob,Grep,AskUserQuestion,TodoWrite
---

# 微信读书笔记导出与知识卡片生成

## 功能概述

自动从微信读书网页版抓取用户的读书笔记（划线、想法），并通过 AI 整理成结构化的知识卡片。

## 使用场景

- 用户想要导出微信读书的笔记
- 用户想要整理读书笔记成知识卡片
- 用户说"帮我整理微信读书的笔记"
- 用户想要生成某本书的读书总结

## 前置条件

1. **Python 环境**: Python 3.9+
2. **依赖安装**:
   ```bash
   cd /home/snape/skills/skills/wechat-read-export
   pip install -r requirements.txt
   playwright install chromium
   ```
3. **微信读书账号**: 需要有微信读书账号并有读书笔记

## 工作流程

### 步骤 1: 确认用户需求

询问用户：
- 要处理哪些书籍的笔记？（全部 / 指定书籍）
- 输出格式偏好？（默认 Markdown）

### 步骤 2: 认证与数据抓取

```bash
cd /home/snape/skills/skills/wechat-read-export
python -m src.main scrape [--book "书名"]
```

**认证流程**:
1. 首次运行会打开浏览器，显示微信读书登录页面
2. 用户扫码登录后，Cookie 会自动保存
3. 后续运行会自动使用已保存的 Cookie

**如果 Cookie 过期**:
```bash
python -m src.main login  # 重新登录
```

### 步骤 3: 生成知识卡片

```bash
python -m src.main generate [--book "书名"] [--output ./output]
```

### 步骤 4: 完整流程（抓取 + 生成）

```bash
python -m src.main run [--book "书名"]
```

## 命令参考

| 命令 | 描述 |
|------|------|
| `python -m src.main login` | 登录微信读书（扫码） |
| `python -m src.main scrape` | 抓取所有书籍笔记 |
| `python -m src.main scrape --book "书名"` | 抓取指定书籍笔记 |
| `python -m src.main generate` | 生成所有书籍的知识卡片 |
| `python -m src.main run` | 完整流程：抓取 + 生成 |
| `python -m src.main list` | 列出已抓取的书籍 |

## 输出格式

### Markdown 知识卡片

每本书生成一个 Markdown 文件，包含：

```markdown
# 《书名》知识卡片

## 书籍信息
- **作者**: xxx
- **划线数量**: 42
- **导出时间**: 2024-01-15

## 核心观点
> AI 生成的书籍核心观点总结

## 精华摘录

### 第一章：xxx
> 原文摘录内容...

**AI 解读**: ...

## 主题标签
#标签1 #标签2
```

## 配置文件

配置文件位于 `config/config.yaml`：

```yaml
weread:
  cookie_path: ~/.wechat-read-export/cookies.json
  headless: false  # 首次登录需要设为 false

output:
  directory: ./output
  format: markdown

ai:
  provider: anthropic
  model: claude-sonnet-4-20250514
```

## 错误处理

### Cookie 过期
```
错误: Cookie 已过期，请重新登录
解决: python -m src.main login
```

### 网络问题
```
错误: 无法连接到微信读书
解决: 检查网络连接，稍后重试
```

## 数据存储

- **Cookie**: `~/.wechat-read-export/cookies.json`
- **抓取数据**: `~/.wechat-read-export/data/`
- **输出文件**: `./output/` (可配置)

## 注意事项

1. 首次运行需要扫码登录，请确保 `headless: false`
2. 抓取大量笔记可能需要较长时间
3. AI 生成需要配置 ANTHROPIC_API_KEY 环境变量
