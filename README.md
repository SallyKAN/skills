# Skills

English | [中文](README.zh-CN.md)

A collection of custom skills for Claude Code that extend Claude's capabilities with specialized knowledge, workflows, and tool integrations.

## About Skills

Skills are folders of instructions, scripts, and resources that Claude loads dynamically to improve performance on specialized tasks. Skills teach Claude how to complete specific tasks in a repeatable way.

For more information about skills, see:
- [What are skills?](https://support.claude.com/en/articles/12512176-what-are-skills)
- [Using skills in Claude](https://support.claude.com/en/articles/12512180-using-skills-in-claude)
- [How to create custom skills](https://support.claude.com/en/articles/12512198-creating-custom-skills)

## Installation

### Option 1: Claude Code Plugin (Recommended)

Register this repository as a Claude Code Plugin marketplace:

```
/plugin marketplace add SallyKAN/skills
```

Then install the skills you need:
```
/plugin install paper-translator-skills@sally-skills
/plugin install flomo-gtd@sally-skills
/plugin install wechat-read-export@sally-skills
```

### Option 2: Manual Installation

1. Clone this repository
```bash
git clone https://github.com/SallyKAN/skills.git
```

2. Copy desired skill folders to:
   - `~/.claude/skills/` - for personal use
   - `.claude/skills/` - for project-specific use

## Available Skills

---

### paper-translator

Automated academic paper to WeChat article translation pipeline. Converts academic papers (arXiv, PDF) into engaging WeChat Official Account articles.

**Features:**
- PDF parsing and figure extraction
- LLM-based article generation (Claude/GPT)
- Reflection-based quality refinement
- AI cover image generation
- WeChat Official Account publishing

**Quick Start:**

1. Install the skill:
   ```
   /plugin install paper-translator-skills@sally-skills
   ```

2. Natural language trigger:
   > "Help me translate this paper to a WeChat article: https://arxiv.org/abs/1706.03762"

See [skills/paper-translator/SKILL.md](skills/paper-translator/SKILL.md) for full documentation.

---

### flomo-gtd

Process Flomo inbox notes using GTD (Getting Things Done) methodology.

**Features:**
- Browser automation scraping via Playwright
- HTML export parsing (backup method)
- GTD-based note categorization
- Todoist integration for task creation

**Quick Start:**

1. Install the skill:
   ```
   /plugin install flomo-gtd@sally-skills
   ```

2. Natural language trigger:
   > "Help me process my Flomo inbox with GTD"

See [skills/flomo-gtd/SKILL.md](skills/flomo-gtd/SKILL.md) for full documentation.

---

### wechat-read-export

Export WeChat Read (微信读书) notes and generate AI-powered knowledge cards.

**Features:**
- Browser automation for WeChat Read web scraping
- Cookie-based authentication with auto-save
- AI-powered knowledge card generation
- Markdown output format

**Quick Start:**

1. Install the skill:
   ```
   /plugin install wechat-read-export@sally-skills
   ```

2. Natural language trigger:
   > "Help me export my WeChat Read notes"

   or

   > "Organize my reading notes into knowledge cards"

See [skills/wechat-read-export/SKILL.md](skills/wechat-read-export/SKILL.md) for full documentation.

---

## Creating New Skills

Use the template in `template/` as a starting point:

```markdown
---
name: my-skill-name
description: A clear description of what this skill does and when to use it
---

# My Skill Name

[Add your instructions here]
```

### Skill Structure

```
my-skill/
├── SKILL.md          # Required: Main documentation and instructions
├── reference.md      # Optional: Reference documentation
├── examples.md       # Optional: Usage examples
├── scripts/          # Optional: Helper scripts
├── templates/        # Optional: Template files
└── requirements.txt  # Optional: Python dependencies
```

### SKILL.md Format

**Required fields:**
- `name`: Unique identifier (lowercase letters, numbers, hyphens, max 64 chars)
- `description`: What the skill does and when to use it (max 1024 chars)

**Optional fields:**
- `allowed-tools`: Restrict which tools Claude can use (e.g., `Read, Grep, Glob`)

## Project Structure

```
skills/
├── .claude-plugin/
│   └── marketplace.json    # Claude Code plugin config
├── skills/
│   ├── paper-translator/   # Paper translator skill
│   ├── flomo-gtd/          # Flomo GTD processor
│   └── wechat-read-export/ # WeChat Read notes export
├── template/
│   └── SKILL.md            # New skill template
├── README.md               # English docs
├── README.zh-CN.md         # Chinese docs
└── .gitignore
```

## Contributing

Contributions are welcome!

1. Fork this repository
2. Create your feature branch (`git checkout -b feature/amazing-skill`)
3. Commit your changes (`git commit -m 'Add amazing skill'`)
4. Push to the branch (`git push origin feature/amazing-skill`)
5. Open a Pull Request

## FAQ

### Q: What's the difference between a Skill and a Prompt?

A: A Skill is a complete package containing instructions, scripts, and resources, while a Prompt is just text instructions. Skills can include multiple files, tool permission restrictions, Python scripts, etc.

### Q: How do I debug my Skill?

A:
1. Activate the skill in Claude Code with `/skill my-skill-name`
2. Observe Claude's responses
3. Adjust the instructions in SKILL.md as needed

### Q: How do I share my Skill?

A:
1. Upload to a GitHub repository
2. Organize according to this repository's format
3. Share your repository link with the community

## Resources

- [Claude Code Official Docs](https://code.claude.com/docs)
- [Agent Skills Standard](http://agentskills.io)
- [Anthropic Official Skills Repository](https://github.com/anthropics/skills)

## License

MIT License

---

If this project helps you, please give it a Star!

Questions or suggestions? Open an [Issue](https://github.com/SallyKAN/skills/issues)
