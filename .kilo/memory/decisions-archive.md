---
type: project
created: 2026-07-24
---

# Decisions Archive

> Cold storage for decisions pruned out of `MEMORY.md` to stay under the
> `memory_gate` hard cap (8,000 chars). **NOT loaded automatically into any
> session** — unlike `MEMORY.md`, this file has no size limit and no
> auto-injection, so pruning here costs nothing per-session regardless of
> how large context windows get (see MEMORY.md "Decisions" for the
> reasoning: a bigger context window should fund per-task budget, not a
> bigger recurring preamble). Grep this file on demand when you need the
> "why" behind an old decision that `git log` alone makes hard to find.
>
> Workflow: when `MEMORY.md`'s Decisions section approaches the cap, MOVE
> (don't delete) the oldest/least-referenced entry here verbatim, then keep
> pruning until back under the WARN threshold (4,000 chars).

## Decisions

- [decision] 2026-07-23: `.opencode/` deprecated (v3.7.0) — verified via `diff` a
  100% content mirror of `.kilo/` (14 agents, 47 skills); only unique asset
  (`command/ship.md`) ported to `.kilo/command/` + `.claude/commands/`.
  Physical removal planned for v4.0.0. (Superseded by the "Phase 3" physical-
  removal entry in `MEMORY.md` — kept here only as the original announcement.)

- [decision] 2026-07-23: reviewed Anthropic's official Claude Code prompt
  library — ~90% of categories already covered by existing `.kilo/skill/`
  entries; added 2 genuine gaps as new skills: `steering-and-course-
  correction`, `incident-investigation`. Skill count 47->49, synced across
  kilo/claude/copilot (gemini lagged by 3 — flagged as a gap, closed next).

- [decision] 2026-07-23: `tools/deploy.py` manifest trimmed — target projects
  get only RUNTIME harness assets (agents/skills/commands/hooks/config), never
  Solo-Code-CLI's own dev tooling, meta docs, CI workflows, or this repo's
  accumulated memory (blank per-engine templates instead). -21% scaffold size
  (1036->845 files).

- [decision] 2026-07-23: closed the Gemini parity gap — added the missing 3
  skills + 3 instruction files, added `check_gemini()` to `garden.py` (Gemini
  models `.gemini/antigravity/` structure; uses `knowledge/artifacts` instead
  of a MEMORY.md-shaped mirror, so no memory parity check applies there). All
  4 engines now genuinely at parity (49 skills, all instructions).

- [decision] 2026-07-23: re-verified `deploy.py` end-to-end after the day's
  changes; found and fixed one real gap: handoff `inbox/outbox/` accumulated
  task files (`*-plan.md`/`*-report.md`) were NOT excluded from deploy — same
  leak class as the earlier MEMORY.md leak, just not yet triggered. Fixed
  `should_copy()` to exclude task instances while still deploying the empty
  protocol scaffold (README.md, .gitkeep).
