---
slug: garden-count-check
created: 2026-07-26
from: claude
status: pending
---

# Task

Implement a new drift check in `tools/garden.py` that catches the exact class
of bug your previous audit found: **hardcoded asset counts in documentation
that no longer match the filesystem.**

## Background

`garden.py` already checks agent/skill/instruction/command *parity* between
`.kilo/` (source of truth) and the mirrors, but nothing verifies the *numbers
written in prose*. That is why `.gemini/antigravity/AGENTS.md` could say
"32 skills, 15 agents" for months with every gate green.

## What to implement

1. In `tools/garden.py`, add a function:

   ```python
   def check_doc_counts() -> list[str]:
   ```

   It must:
   - Measure ground truth from `.kilo/`: skills = subdirectories of
     `.kilo/skill/`, agents = `*.md` in `.kilo/agents/`, commands = `*.md`
     in `.kilo/command/`, instructions = `*.md` in `.kilo/instruction/`.
   - Scan these files for count claims that disagree with ground truth:
     `AGENTS.md`, `CLAUDE.md`, `README.md`,
     `.github/copilot-instructions.md`, `.gemini/antigravity/AGENTS.md`,
     `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`
   - Return a list of human-readable issue strings (same style as the other
     `check_*` functions in that file). Empty list = clean.

2. Register it in the checks list so `python tools/garden.py` runs it.

3. Add tests to `tools/test_garden.py` covering: (a) it flags a wrong count,
   (b) it does not flag a correct count.

## Scope constraints (IMPORTANT — read carefully)

- Modify **only** these two files: `tools/garden.py`, `tools/test_garden.py`.
- **Do NOT fix any of the drifts you find.** You will almost certainly make
  `python tools/garden.py` start FAILING, because there are ~12 real stale
  counts in the repo right now. **That failure is the expected, correct
  outcome of this task.** Do not "helpfully" edit `README.md`, `AGENTS.md`,
  `.claude-plugin/*.json` or any other file to make the gate go green.
  I will fix those myself, separately, after reviewing.
- Must remain **stdlib-only** (no new dependencies). This repo's `tools/`
  has zero external deps.
- Do not exclude/allowlist files just to make the check pass.
- Do NOT edit `.gemini/antigravity/handoff/inbox/garden-count-check-plan.md`
  (this file). Leave `status: pending`. I track status on my side now.

## Deliverable

Write `.gemini/antigravity/handoff/outbox/garden-count-check-report.md`:

```
---
slug: garden-count-check
completed: <ISO date>
from: gemini
---
```

Then:

1. **What I changed** — one line per file, what was added.
2. **Verification** — a table. For each claim you make about your work,
   give the *exact command* you ran and its actual output (trimmed):

   | Claim | Command run | Output (trimmed) |

   At minimum verify: the new tests pass, ruff is clean on both files,
   and `python tools/garden.py` now reports the stale counts.
   Do not write a claim you did not actually run a command for.
3. **Counts my check currently flags** — just the list, do not fix them.
4. **Anything I was unsure about** — if nothing, write "nothing".

Keep the report under 120 lines.
