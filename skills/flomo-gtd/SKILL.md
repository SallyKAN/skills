---
name: flomo-gtd
description: Process Flomo inbox notes using GTD methodology. Use when user wants to process their Flomo inbox, do GTD review, or organize their captured thoughts into actionable items. Automatically scrapes Flomo data via browser automation, analyzes each note with GTD principles, and optionally creates tasks in Todoist.
allowed-tools: Bash,Read,Write,Edit,AskUserQuestion,TodoWrite
---

# Flomo GTD Processor

This skill processes Flomo inbox notes using the Getting Things Done (GTD) methodology. It automatically scrapes your Flomo data using browser automation, analyzes each note, and helps organize them into actionable categories.

## When to Use This Skill

Activate this skill when the user:
- Wants to process their Flomo inbox
- Asks for GTD review of their notes
- Wants to organize captured thoughts into actions
- Mentions "flomo gtd", "process inbox", or "review flomo notes"

## Prerequisites

1. **Python Dependencies**:
   ```bash
   pip install playwright beautifulsoup4 requests
   playwright install chromium
   ```

2. **First-time Login** (one-time setup):
   ```bash
   python3 /path/to/skills/flomo-gtd/src/flomo_scraper.py --login
   ```
   This opens a browser for you to log in manually. After login, the session is saved for future use.

3. **Todoist API Token** (optional): For creating tasks
   - Get from: https://todoist.com/app/settings/integrations/developer
   - Store in environment variable: `TODOIST_API_TOKEN`

## GTD Categories

Each note will be classified into one of these categories:

| Category | Description | Action |
|----------|-------------|--------|
| **Trash** | Not useful, outdated, or irrelevant | Archive/Delete |
| **Reference** | Useful info but no action needed | Tag as `#reference` |
| **Someday/Maybe** | Interesting but not now | Tag as `#someday` |
| **Next Action** | Single actionable task | Create Todoist task |
| **Project** | Multi-step outcome | Create Todoist project |
| **Waiting For** | Delegated or waiting on someone | Tag as `#waiting` |
| **Calendar** | Time-specific commitment | Note the date |
| **Unclear** | Need more context from user | Ask for clarification |

## Workflow

### Step 1: Check Session and Auto-Scrape Notes

First, check if a valid session exists and scrape notes automatically:

```bash
# Check if session exists
ls -la ~/.flomo-gtd/browser_state.json 2>/dev/null

# If no session, prompt user to login first
python3 /path/to/skills/flomo-gtd/src/flomo_scraper.py --login

# Scrape inbox notes automatically
python3 /path/to/skills/flomo-gtd/src/flomo_scraper.py --tag inbox --output /tmp/flomo_inbox.json

# Or scrape all notes
python3 /path/to/skills/flomo-gtd/src/flomo_scraper.py --all --output /tmp/flomo_all.json
```

If the session has expired, the scraper will notify you. Run `--login` again to refresh.

### Step 2: Load and Parse Notes

Read the scraped JSON file:

```bash
cat /tmp/flomo_inbox.json
```

### Alternative: Manual HTML Export (Fallback)

If browser automation doesn't work, users can still export manually:
1. Open Flomo app or web
2. Go to Settings (gear icon)
3. Find "Data Export" or "Export All"
4. Download the ZIP file
5. Use the HTML parser:

```bash
python3 /path/to/skills/flomo-gtd/src/parse_flomo.py /path/to/flomo/export --tag inbox
```

### Step 3: GTD Analysis

For each inbox note, analyze using these GTD questions:

1. **What is it?** - Understand the content
2. **Is it actionable?**
   - NO → Is it useful reference? → Reference or Trash
   - YES → Continue to next question
3. **What's the next action?**
   - Can it be done in 2 minutes? → Do it now
   - Is it a single action? → Next Action
   - Does it require multiple steps? → Project
4. **Who should do it?**
   - Me → Next Action or Project
   - Someone else → Waiting For
5. **When should it be done?**
   - Specific date/time → Calendar
   - When possible → Next Action
   - Someday → Someday/Maybe

### Step 4: Present Analysis to User

For each note, present:
```
---
Note #1: [First 50 chars of content...]
Created: [date]
Full content: [content]

GTD Analysis:
- Category: [category]
- Reasoning: [why this category]
- Suggested action: [what to do]
- Todoist task (if applicable): [task title]

[Accept] [Change Category] [Skip]
---
```

### Step 5: Execute Actions

Based on user confirmation:

**For Next Actions / Projects → Create Todoist Task**
```bash
python3 /path/to/skills/flomo-gtd/src/todoist_client.py add-task \
  --content "Task title" \
  --description "Original flomo note content" \
  --project "Inbox" \
  --priority 1
```

**For Reference → Suggest new tag**
```
Suggest adding #reference tag in Flomo
```

**For Someday/Maybe → Suggest new tag**
```
Suggest adding #someday tag in Flomo
```

### Step 6: Generate Report

Create a summary report:
```markdown
# Flomo GTD Processing Report
Date: [date]

## Summary
- Total inbox notes processed: X
- Next Actions created: X
- Projects identified: X
- Reference items: X
- Someday/Maybe: X
- Trash: X

## Next Actions Created in Todoist
1. [Task 1]
2. [Task 2]
...

## Projects Identified
1. [Project 1] - [first action]
...

## Reference Items
- [Note summary 1]
...

## Someday/Maybe
- [Note summary 1]
...

## Notes for Review
- [Any unclear items]
```

## Interactive Mode

When processing notes, always:
1. Show the note content
2. Explain your GTD classification reasoning
3. Ask for confirmation before taking action
4. Allow user to override classification
5. Batch similar items when possible

## Configuration

Create `~/.flomo-gtd-config.json`:
```json
{
  "todoist_api_token": "your-token-here",
  "default_project": "Inbox",
  "auto_confirm_trash": false,
  "auto_confirm_reference": false,
  "export_path": "~/Documents/flomo-gtd-reports"
}
```

## Error Handling

- If no session found: Run `python3 /path/to/skills/flomo-gtd/src/flomo_scraper.py --login` to authenticate
- If session expired: The scraper will notify you. Run `--login` again to refresh
- If scraping fails: Fall back to manual HTML export method
- If Todoist token missing: Skip Todoist integration, just classify
- If note is ambiguous: Always ask user for clarification
- If parsing fails: Show raw content and ask user to interpret

## Tips

- Process inbox regularly (weekly review)
- Don't overthink classification - trust your gut
- When in doubt, it's probably a Next Action
- Projects need a clear outcome and multiple steps
- Reference is for things you might need later
- Trash is for things that no longer matter
