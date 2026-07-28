---
allowed-tools: Write, Read
description: Save a convention, gotcha, or preference to cross-session persistent memory
---

## Task

Save important information to persistent memory so it survives across sessions.

### Memory Format
```markdown
---
name: <short-kebab-case-slug>
description: <one-line summary>
metadata:
  type: user | feedback | project | reference
---

<the fact; for feedback/project, follow with **Why:** and **How to apply:** lines>
```

### Memory Types
- **project** — conventions, gotchas, architectural decisions
- **feedback** — corrections, confirmed approaches, preferences
- **reference** — URLs, dashboards, external resources
- **user** — who the user is, expertise, preferences

### Location
- Project memory: `.gemini/antigravity/knowledge/artifacts/` (one file per fact)
- Index: `.gemini/antigravity/knowledge/metadata.json`

Gemini stores knowledge as artifacts + a metadata index — it has no
`MEMORY.md` mirror like the other engines (see `check_gemini()` in
`tools/garden.py`). Do not create one; garden does not check for it.

### Before Saving
- Check if an existing memory file already covers this → update instead of duplicating
- Don't save what the repo already records (code structure, git history, CLAUDE.md)
- Don't save what only matters to this conversation
