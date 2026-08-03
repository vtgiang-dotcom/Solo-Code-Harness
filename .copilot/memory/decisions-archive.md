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

- [decision] 2026-07-28: **rejected Linear (and Notion) for issue tracking**
  -- keep git log + `MEMORY.md`. The deciding evidence is local, not
  opinion: after 9 days of real use `shared_state.db` held `session_log`
  350 rows but `features` **0**, `active_locks` 0, `shared_memory_*` 0.
  `session_log` fills because hooks write it automatically; `features`
  stays empty because it needs a human to call `set_feature_status()` --
  which no executable code ever does. Since a local SQLite table that is
  free, offline and one Python call away still went unused, a tool that
  costs OAuth + network + context window will not fare better. General
  rule extracted: **anything that depends on a human remembering to
  update it will drift.** Corollary for evaluating any future tracker:
  ask whether *work* updates it (git: commit/PR/CI) or a *person* does
  (Linear/Notion) -- git measures progress, trackers only display what
  someone typed. To reopen this, the trigger is a second **person**, not
  a second agent: concurrent agents are already handled by `active_locks`
  (2026-07-26), which trackers cannot do -- they have no file-level
  locking and second-scale latency. Note `active_locks` only works for
  agents on ONE machine (DB is gitignored, local-only); distributed
  humans fall back to branches + PRs. When that day comes, try **GitHub
  Issues first** (remote already exists, `.mcp.json` already documents
  enabling GitHub MCP, and `fixes #N` closes issues automatically -- so
  it lands in the "work updates it" class), and escalate to Linear only
  for cycles/estimates/roadmaps or non-developer teammates. Already
  verified so nobody re-probes it: Linear MCP is
  `https://mcp.linear.app/mcp` (HTTP 401 + `WWW-Authenticate: Bearer
  realm="OAuth"`, scopes read/write, no API key in config); the older
  `/sse` endpoint is dead (404). Also deleted a vendored 18MB
  `linear-master/` SDK checkout that was untracked AND ungitignored --
  one `git add -A` from entering the repo.

- [decision] 2026-07-26: made Gemini/Antigravity a first-class worker
  alongside jcode, after two controlled tests. Root problem: the harness
  *pushed* jcode into every session (`_jcode_available()` + a trigger-rich
  `jcode-delegation` skill) but mentioned Gemini only when a report already
  existed in `outbox/` -- so Gemini was structurally forgotten, not
  forgotten by accident. Fixed by mechanism, not memory: added
  `_gemini_available()` (needs BOTH handoff/inbox AND the IDE installed),
  a `gemini-delegation` SKILL.md, and a routing table in AGENTS.md/CLAUDE.md.
  Measured payoff: a repo-wide audit cost Gemini ~49.6k tokens of reading vs
  ~2.5k of ours (~20x leverage). Measured limit: BOTH tests shipped an error
  invisible in its own self-summary (1 wrong finding marked "Confident: Yes";
  2 false positives while reporting "unsure: nothing"). Standing rule --
  its evidence is reliable, its self-assessment is not; verify 100%. Also
  killed the `status:` contradiction (plan files are read-only for Gemini;
  the report's existence is the completion signal) and banned re-litigating
  headless access: the SDK has no OAuth path to the Pro plan and
  `antigravity-ide chat` only drives the GUI.

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
- [decision] 2026-07-24: added Context Summary Struct to PreCompact +
  decisions-archive.md tier. `pre_compact.py` asks Claude to write
  `.solocode/context-checkpoint.json` (active_feature, unverified_changes,
  settled_decisions, next_immediate_step); `session_start.py` surfaces it
  once next session then deletes it (recovery aid, not mid-compaction
  survival -- a hook can't guarantee that). Bigger context windows should
  NOT raise MEMORY.md's cap: it's a recurring per-session cost across all 5
  engines (sized for the weakest, jcode), not a one-time budget. Instead
  added `.kilo/memory/decisions-archive.md` (uncapped, not auto-loaded) --
  pruning now MOVES entries there, not deletes. Also `/debug` now requires
  >=2 hypotheses (all 4 engines). Verified: 0 drift, 107 tests.
- [decision] 2026-07-24: verified jcode/DeepSeek delegation end-to-end
  (real "pong" response); `--tool-profile none --no-selfdev` cuts input
  tokens ~65% (22,376->7,709). Bigger finding: `CLAUDE.md` was NOT actually
  generated from `AGENTS.md` -- `claude_engine.py`'s template is hand-
  written, only parameterized by counts. The earlier Gemini-handoff section
  (added to AGENTS.md) had silently never reached real CLAUDE.md. Fixed:
  added Gemini + jcode delegation sections into the template + regenerated;
  fixed a stale `tools/test_harness.py` ref (deleted v4.0.0) -> `pytest
  tools/ -q`. Added `_jcode_available()` to `session_start.py`. Also fixed
  CI/Makefile hardcoded test-file allowlist (missed test_garden.py/
  test_integration.py), test_integration.py's machine-specific >=19-feature
  assertion, rewrote stale SPEC.md (v3.3.0->v4.1.0), removed suggest.md.
- [decision] 2026-07-25: upgraded `claude-env.ps1` for FreeModel 4-domain
  multi-tier support: normalize `/v1/messages` for api.freemodel.dev (canonical
  from guide.md), cc.freemodel.dev, api-cc.freemodel.dev, cc-t2.freemodel.dev.
  Added apiKeyHelper conflict detection: if `~/.claude/settings.json` has
  `apiKeyHelper` configured, automatically unset `ANTHROPIC_API_KEY` to
  eliminate the "Both apiKeyHelper and ANTHROPIC_API_KEY set" warning.
  Updated `.env.template` with 3-tier VIP documentation (Standard/Mid/Top).
- [decision] 2026-07-25: **removed the jcode two-tier model split** — real
  usage showed `deepseek-v4-flash` unreliable, its token savings lost to
  re-prompting and orchestrator rework, and the routing choice itself a
  recurring source of judgment error. `tools/jcode_delegate.py` is now
  single-model: `deepseek-v4-pro` on every call with the guardrail preamble
  (renamed `CODE_TIER_GUARDRAIL` -> `GUARDRAIL`) always prepended; dropped
  `MODELS`/`classify_tier`; `--tier` kept as an ignored, deprecation-warning
  no-op so older callers don't break; usage log no longer writes `tier`.
  Cost optimization now comes only from flag discipline (`--tool-profile
  none --no-selfdev`, ~65% fewer input tokens), which costs no quality.
  Synced jcode.ps1 default, README, AGENTS.md, CLAUDE.md + its generator
  template, and the skill across all 4 engines.
- [decision] 2026-07-25: fixed the `CLAUDE.md` generator gap found while
  doing the above. `claude_engine.py`'s `_CLAUDE_MD_TEMPLATE` had silently
  fallen behind the hand-edited live `CLAUDE.md`, so regenerating would
  have DELETED real content — exactly what the file's "do not edit by
  hand" banner is meant to prevent, with nothing verifying it. Ported the
  live content back into the template (regeneration is now lossless +
  idempotent) and added `garden.check_claude_md_regenerable()` so the
  divergence is loud drift instead of a silent landmine; extracted
  `_claude_md_counts()` so the checker renders the template exactly as the
  generator does. Also made generator writes LF-explicit (`_write_lf`):
  `Path.write_text` emits CRLF on Windows, which git hides here but
  `deploy.py` copies verbatim into non-git target projects. +3 tests (123).

- [decision] 2026-07-25: repaired `verify.sh` (6/31 -> 31/31 PASS). Root
  causes, all silent: (a) it probed `command -v python3`, which on Windows
  resolves to a Microsoft Store *stub* that exits with an install prompt --
  so every gated garden/test check "failed" while passing when run directly;
  now probes by executing `-c "import sys"`. (b) stale paths: `.claude/
  CLAUDE.md` -> `CLAUDE.md`, flat `.claude/skills/$sk.md` -> `$sk/SKILL.md`,
  `pytest tools/test_harness.py` (deleted v4.0.0) -> `pytest tools/ -q`,
  node guard test -> `pytest tools/test_claude_guard.py`. (c) the `socratic`
  keyword check was NOT stale -- CLAUDE.md genuinely lacked AGENTS.md's
  Complex Tasks section, so fixed the source template in `claude_engine.py`
  rather than deleting the check. Security: whitelisted vendored
  `antigravity-sdk-python-main` in security_scan SKIP_DIRS (fake fixture
  string) and added a `bcrypt/scrypt/argon2` gitleaks regex allowlist (it
  read password-hashing *prose* as an assignment). Fault-injected a real
  fake secret into both scanners afterward to prove they still fire -- an
  allowlist that disables detection is worse than the false positive.
