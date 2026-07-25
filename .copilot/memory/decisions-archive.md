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

- [decision] 2026-07-23: adopted **jcode** (DeepSeek v4 via CommandCode) as the
  cost/latency-optimized worker engine, orchestrated by Claude Code. Benchmarked
  ~2-9x faster startup, ~15-63x lower RAM than OpenCode for concurrent workers.
  No dedicated dir — reads `AGENTS.md` + `.claude/skills/` + `.mcp.json`
  natively. Launch via `jcode.ps1`.
- [decision] 2026-07-23: Phase 3 — `.opencode/` physically removed via `git rm`
  (reversible), vendored `jcode-master/` source removed after installing
  compiled `jcode.exe` to PATH. Version bumped to v4.0.0 across
  `.harness.lock`/`agent.yaml`/`garden.py`/`generate_harness.py`/
  `validate_schemas.py`/docs. `.copilot/memory` synced manually (no
  auto-generator; parity is check-only via `garden.py`). Verified: 0 drift,
  full test suite green on a fresh live scaffold.

- [decision] 2026-07-23: added a `PreCompact` lifecycle hook
  (`.claude/hooks/pre_compact.py`) for context-compaction continuity — logs an
  objective checkpoint (git branch/sha/dirty count) to `.solocode/shared-
  state.db` before every compaction, and reminds Claude via `additionalContext`
  to append any settled decision to `.kilo/memory/MEMORY.md` first. Added a
  required-hook check to `garden.py`'s `check_claude()` + 4 new tests. Kilo Code
  has no equivalent lifecycle event — rule applied manually there instead.
- [decision] 2026-07-23: added a file-based Claude<->Gemini/Antigravity handoff
  protocol (`.gemini/antigravity/handoff/{inbox,outbox}/`, git-tracked audit
  trail, separate from the static `knowledge/` corpus). No headless CLI exists
  for Antigravity, so a human relay step is unavoidable — reduced to "read
  file X, write file Y" instead of copy-pasting. `session_start.py` auto-
  announces new `outbox/*-report.md` files once via a local seen-marker.

- [decision] 2026-07-24: audited the memory system after a direct user
  question ("does SQLite belong in project memory too?"). Found two real
  gaps: (1) `garden.py`'s `check_memory()` only checked filename parity, not
  content — `.claude/memory/MEMORY.md` had silently drifted 19 lines behind
  this file (source of truth) with no drift ever reported; (2) Kilo's
  `memory-manager.js` size gate (WARN 4k/HARD 8k chars) was never ported to
  Claude Code, so writes to `.claude/memory/` had no size cap at all — this
  file had already grown past both thresholds (13.4k chars) undetected.
  Fixed both: `check_memory()` now diffs file content byte-for-byte, not just
  existence; added `.claude/hooks/memory_gate.py` (Python port of memory-
  manager.js, exit(2) hard-blocks PostToolUse on Edit/Write/MultiEdit past
  8k chars) wired into `.claude/settings.json` + required in `garden.py`'s
  `check_claude()`. Also compacted this Decisions section itself (verbose
  paragraphs -> concise one-liners; full detail already durable in git commit
  history) to bring all three memory mirrors back under the WARN threshold.
  Confirmed: SQLite (`.solocode/shared-state.db`) is correctly scoped to
  cross-engine coordination state (locks/feature status) only, never
  project memory/decisions — that split is intentional, not a gap.
- [decision] 2026-07-24: removed `docs/specs/` (8 files, obsolete OpenCode
  planning docs + completed plans; history in git log). Fixed real content
  drift in `.copilot`/`.gemini`: both mirrored from an older `.kilo/` and
  never re-synced — missing the Fowler Smell Baseline section in
  `code-review-expert/SKILL.md` + a point in `interview-me/SKILL.md`
  (identical gap in both). Synced body content, kept each engine's own
  frontmatter. `garden.py` now diffs real content:
  `check_skill_content()` (frontmatter-agnostic) + `check_instruction_
  content()` (byte-for-byte). Added `tools/test_garden.py` (14 tests).
