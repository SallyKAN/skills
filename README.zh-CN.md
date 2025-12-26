# Skills / 技能集合

[English](README.md) | 中文

Claude Code 自定义技能集合，通过专业知识、工作流程和工具集成扩展 Claude 的能力。

## 关于 Skills

Skills 是包含指令、脚本和资源的文件夹，Claude 可以动态加载它们以提高在专业任务上的表现。Skills 教会 Claude 如何以可重复的方式完成特定任务。

更多关于 skills 的信息，请参见：
- [什么是 skills?](https://support.claude.com/en/articles/12512176-what-are-skills)
- [在 Claude 中使用 skills](https://support.claude.com/en/articles/12512180-using-skills-in-claude)
- [如何创建自定义 skills](https://support.claude.com/en/articles/12512198-creating-custom-skills)

## 可用的 Skills

### paper-translator / 论文翻译器

自动化的学术论文到微信文章的翻译流程。将学术论文（arXiv、PDF）转换为引人入胜的微信公众号文章，包含：

- PDF 解析和图表提取
- 基于 LLM 的文章生成（Claude/GPT）
- 基于反思的质量优化
- AI 封面图生成
- 微信公众号发布

**使用方法：**
```bash
python -m src.main https://arxiv.org/abs/1706.03762
```

查看完整文档：[skills/paper-translator/SKILL.md](skills/paper-translator/SKILL.md)

#### 主要特性

🚀 **完整的自动化流程**
- 支持 arXiv URL 和 PDF 直链
- 自动下载和解析论文内容
- 提取论文中的图表和公式

🤖 **智能写作系统**
- 双引擎支持（Claude/GPT）
- 通俗易懂的科普写作风格
- 二次反思润色提升质量

🎨 **自动配图**
- 提取论文原图
- AI 生成封面图
- 支持自定义配图风格

📱 **一键发布**
- 直接发布到微信公众号草稿箱
- Markdown 转微信 HTML 格式
- 自动上传图片到素材库

#### 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/SallyKAN/skills.git
cd skills/skills/paper-translator

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API 密钥
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥

# 4. 运行翻译
python -m src.main https://arxiv.org/abs/1706.03762

# 指定引用量
python -m src.main https://arxiv.org/abs/1706.03762 --citations 100000

# 翻译并发布
python -m src.main https://arxiv.org/abs/1706.03762 --publish
```

#### 配置说明

编辑 `config/config.yaml`:

```yaml
# LLM 配置
llm:
  provider: "anthropic"  # anthropic 或 openai
  model: "claude-sonnet-4-20250514"

# 图片生成
replicate:
  model: "nano-banana-pro"

# 文章配置
article:
  language: "zh-CN"
  style: "通俗易懂、深入浅出"
  audience: "对AI感兴趣的技术爱好者"
  generate_cover: true
  use_paper_figures: true
```

## 安装方式

### 方式 1：Claude Code 插件

在 Claude Code 中注册此仓库为插件市场：

```
/plugin marketplace add SallyKAN/skills
```

然后安装技能：
```
/plugin install paper-translator-skills@sally-skills
```

### 方式 2：手动安装

1. 克隆此仓库
```bash
git clone https://github.com/SallyKAN/skills.git
```

2. 将所需的 skill 文件夹复制到：
   - `~/.claude/skills/` - 个人使用
   - `.claude/skills/` - 项目特定使用

### 方式 3：直接使用源代码

```bash
git clone https://github.com/SallyKAN/skills.git
cd skills/skills/paper-translator
pip install -r requirements.txt
# 按照上面的快速开始运行
```

## 创建新的 Skills

使用 `template/` 中的模板作为起点：

```markdown
---
name: my-skill-name
description: 清晰描述这个技能的作用和使用场景
---

# 我的技能名称

[在此添加你的指令]
```

### Skill 结构

```
my-skill/
├── SKILL.md          # 必需：主要文档和指令
├── reference.md      # 可选：参考文档
├── examples.md       # 可选：使用示例
├── scripts/          # 可选：辅助脚本
├── templates/        # 可选：模板文件
└── requirements.txt  # 可选：Python 依赖
```

### SKILL.md 格式要求

**必需字段：**
- `name`: 技能的唯一标识符（小写字母、数字、连字符，最多 64 字符）
- `description`: 技能的功能和使用场景说明（最多 1024 字符）

**可选字段：**
- `allowed-tools`: 限制 Claude 可以使用的工具（如 `Read, Grep, Glob`）

## 项目结构

```
skills/
├── .claude-plugin/
│   └── marketplace.json    # Claude Code 插件配置
├── skills/
│   └── paper-translator/   # 论文翻译器技能
│       ├── SKILL.md        # 技能文档（含 YAML frontmatter）
│       ├── src/            # 源代码
│       ├── prompts/        # 提示词模板
│       ├── config/         # 配置文件
│       └── requirements.txt
├── template/
│   └── SKILL.md            # 新技能模板
├── README.md               # 英文说明
├── README.zh-CN.md         # 中文说明
└── .gitignore
```

## 贡献指南

欢迎贡献新的 skills 或改进现有 skills！

1. Fork 此仓库
2. 创建你的功能分支 (`git checkout -b feature/amazing-skill`)
3. 提交你的更改 (`git commit -m 'Add amazing skill'`)
4. 推送到分支 (`git push origin feature/amazing-skill`)
5. 开启 Pull Request

### 贡献 Skill 的建议

- 保持 skill 专注于单一任务
- 提供清晰的文档和示例
- 测试 skill 在不同场景下的表现
- 遵循现有 skill 的格式规范

## 常见问题

### Q: Skill 和 Prompt 有什么区别？

A: Skill 是包含指令、脚本、资源的完整包，而 Prompt 只是文本指令。Skill 可以包含多个文件、工具权限限制、Python 脚本等。

### Q: 如何调试我的 Skill？

A:
1. 在 Claude Code 中使用 `/skill my-skill-name` 激活
2. 观察 Claude 的响应
3. 根据需要调整 SKILL.md 中的指令

### Q: Skill 支持哪些编程语言？

A: Skill 本身是语言无关的，但可以包含任何语言的脚本。常见的有 Python、JavaScript、Shell 等。

### Q: 如何分享我的 Skill？

A:
1. 上传到 GitHub 仓库
2. 按照本仓库的格式组织
3. 在社区分享你的仓库链接

## 资源链接

- [Claude Code 官方文档](https://code.claude.com/docs)
- [Agent Skills 标准](http://agentskills.io)
- [Anthropic 官方 Skills 仓库](https://github.com/anthropics/skills)

## 许可证

MIT License

---

⭐ 如果这个项目对你有帮助，欢迎 Star！

📧 有问题或建议？欢迎提 [Issue](https://github.com/SallyKAN/skills/issues)
