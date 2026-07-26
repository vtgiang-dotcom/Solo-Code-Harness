---
slug: stale-counts-audit
created: 2026-07-26
from: claude
status: done
---

# Task

Audit this harness for **hardcoded numbers in documentation that have drifted
from reality**. We already found three cases (see Context). Find the rest.

This is a read-only investigation. Your deliverable is a single report file.

## Context

The harness mirrors `.kilo/` (source of truth) into `.claude/`, `.copilot/`,
and `.gemini/antigravity/`. Several docs state counts like "50 skills" or
"14 agents". `tools/garden.py` does NOT verify these numbers, so they rot
silently whenever a skill or agent is added.

Ground truth is the filesystem:
- skills   = number of directories in `.kilo/skill/`
- agents   = number of `*.md` files in `.kilo/agents/`
- commands = number of `*.md` files in `.kilo/command/`
- instructions = number of `*.md` files in `.kilo/instruction/`

Known cases (already found, use as examples of the pattern — confirm and
include them):
1. `.gemini/antigravity/AGENTS.md` says "32 skills, 15 agents"
2. `AGENTS.md` says "48 skills"
3. `tools/test_integration.py` had hardcoded `expect 10` / `expect 6` counts

Look especially at (but do not limit yourself to):
- `AGENTS.md`, `CLAUDE.md`, `README.md`, `SPEC.md`
- `.github/copilot-instructions.md`
- `.kilo/`, `.claude/`, `.copilot/`, `.gemini/` rulebooks and instructions
- `tools/*.py` and `.github/scripts/*.py`
- `.claude-plugin/`, `agent.yaml`, `kilo.jsonc`

## Constraints (IMPORTANT — please follow exactly)

- **Do NOT modify any file** except the one report file named below.
  Do not "helpfully" fix the numbers you find. I want to review first.
- Do not create scratch/temp files inside the repository.
- Ignore `antigravity-sdk-python-main/` entirely (vendored third-party SDK).
- If you are unsure whether something is drift, include it and say you are
  unsure. Do not guess silently.

## Expected report format

Write to `.gemini/antigravity/handoff/outbox/stale-counts-audit-report.md`
with this frontmatter:

```
---
slug: stale-counts-audit
completed: <ISO date>
from: gemini
---
```

Then a table with these exact columns:

| File | Line | Claim in doc | Actual value | Confident? |

followed by two short sections:
- **Ground truth counts** — the four numbers you measured from `.kilo/`
- **Notes** — anything ambiguous, plus any file you were unable to read

Keep the report under 150 lines. Do not paste large file excerpts.
