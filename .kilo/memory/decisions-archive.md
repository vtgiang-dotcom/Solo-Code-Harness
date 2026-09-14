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
  alongside Kilo CLI, after two controlled tests. Root problem: the harness
  *pushed* Kilo CLI into every session (`_kilo_available()` + a trigger-rich
  `kilo-cli-delegation` skill) but mentioned Gemini only when a report already
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

- [decision] 2026-07-23: adopted **Kilo CLI** as the cost/latency-optimized
  worker engine, orchestrated by Claude Code. Benchmarked ~2-9x faster startup,
  ~15-63x lower RAM than OpenCode for concurrent workers. No dedicated dir —
  reads `AGENTS.md` + `.claude/skills/` + `.mcp.json` natively. Launch via
  Kilo CLI directly.
- [decision] 2026-07-23: Phase 3 — `.opencode/` physically removed via `git rm`
  (reversible), Kilo CLI installed as the worker engine. Version bumped to
  v4.0.0 across
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
  engines (sized for the weakest, Kilo CLI), not a one-time budget. Instead
  added `.kilo/memory/decisions-archive.md` (uncapped, not auto-loaded) --
  pruning now MOVES entries there, not deletes. Also `/debug` now requires
  >=2 hypotheses (all 4 engines). Verified: 0 drift, 107 tests.
- [decision] 2026-07-24: verified Kilo CLI delegation end-to-end (real "pong"
  response); `--tool-profile none --no-selfdev` cuts input tokens ~65%
  (22,376->7,709). Bigger finding: `CLAUDE.md` was NOT actually
  generated from `AGENTS.md` -- `claude_engine.py`'s template is hand-
  written, only parameterized by counts. The earlier Gemini-handoff section
  (added to AGENTS.md) had silently never reached real CLAUDE.md. Fixed:
  added Gemini + Kilo CLI delegation sections into the template + regenerated;
  fixed a stale `tools/test_harness.py` ref (deleted v4.0.0) -> `pytest
  tools/ -q`. Added `_kilo_available()` to `session_start.py`. Also fixed
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
- [decision] 2026-07-25: **removed the Kilo CLI two-tier model split** — real
  usage showed `deepseek-v4-flash` unreliable, its token savings lost to
  re-prompting and orchestrator rework, and the routing choice itself a
  recurring source of judgment error. `tools/kilo_delegate.py` is now
  single-model: `deepseek-v4-pro` on every call with the guardrail preamble
  (renamed `CODE_TIER_GUARDRAIL` -> `GUARDRAIL`) always prepended; dropped
  `MODELS`/`classify_tier`; `--tier` kept as an ignored, deprecation-warning
  no-op so older callers don't break; usage log no longer writes `tier`.
  Cost optimization now comes only from flag discipline (`--tool-profile
  none --no-selfdev`, ~65% fewer input tokens), which costs no quality.
  Synced Kilo CLI defaults, README, AGENTS.md, CLAUDE.md + its generator
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

- [decision] 2026-07-28: closed the **"docs assert infrastructure that
  does not exist"** class with 5 machine gates in `garden.py`, after it
  produced 6 separate bugs that every gate passed for months.
  `check_doc_counts()` (2026-07-26, counts resolve per engine),
  `check_doc_paths()` (cited path must resolve), `check_doc_flags()`
  (documented flag must exist), `check_enforcement_claims()` (a script
  called "blocking" must contain a non-zero exit), `check_skill_refs()`
  (a skill named as a skill must exist). What they caught: `.opencode/*`
  refs surviving the v4.0.0 engine removal; `.claude/state/` called "the
  existing convention" though `git log --all` shows it never existed;
  `tools/eval.py --check-triggers`; `garden.py --strict` on a script with
  zero argv handling; `quality-gate.js` promising to block a missing
  ALGO-CHECK tag while all 3 of its exits are `process.exit(0)`; and the
  router `using-agent-skills` pointing at 5 skills that never existed
  (104 refs x 4 engines) while real counterparts sat under other names.
  Design rule learned the hard way: **verify generously, flag narrowly.**
  Draft 1 of the flag check fired on real subcommand flags (fixed by
  unioning per-subcommand `--help` + source text, since hand-rolled argv
  parsers emit no help); draft 1 of the skill check matched bare
  kebab-case and returned 190 hits, nearly all npm packages and YAML keys
  -- requiring an explicit marker (`` `x` skill ``, `skills/x/SKILL.md`,
  or a router arrow on a line containing `?`) dropped it to 0 while still
  catching all 104. A gate that cries wolf gets disabled, so a false
  positive costs more than a miss. Every gate was fault-injected before
  commit. Standing limit, do not re-litigate without new evidence: these
  check that citations *resolve*, never that prose *descriptions* are
  accurate -- that needs semantics, i.e. an LLM, i.e. non-determinism, and
  a gate that fires only sometimes is worse than none.

- [decision] 2026-08-06: `claude-env.ps1` now supports explicit launcher
  profiles: `gateway` (default, FreeModel/third-party via `--bare`),
  `native` (full mode, prefer API key or `apiKeyHelper` if present), and
  `kilo` (full-mode alias for IDE-integrated Kilo workflows). This keeps the
  current Claude gateway path stable, avoids touching `COMMANDCODE_*`/`DEEPSEEK_*`, and makes Kilo-specific IDE integrations opt-in
  instead of overloading one implicit runtime path.   `gateway` still restores
  `CLAUDE.md` discovery with `--add-dir .`, but hooks/auto-memory remain a
  documented degraded mode under `--bare`.
- [decision] 2026-09-10: OpenCode no longer mirrors skills into
  `.opencode/skills/`. OpenCode natively loads `.opencode/skills/` AND the
  Claude-compatible `.claude/skills/`, and requires skill names to be unique
  across loaded locations; mirroring `.kilo/skill` into both registered every
  skill twice. It now relies on `.claude/skills/` alone;
  `tools/opencode_engine.prune_duplicate_skills()` removes any legacy
  `.opencode/skills/`, and `garden.check_opencode()` flags a stray one.
  `deploy.py --engine opencode` ships `.claude/skills/` (and no longer creates
  a stray `.claude/memory/`). Lint budget lowered 75->72 (one fewer
  `mcp-builder/scripts/evaluation.py` copy -> -3 S/BLE findings). Also:
  AGENTS.md + `harness-boundaries.md` corrected — `.opencode/` is a
  first-class engine (v4.2.0) that was only briefly removed, not current; and
  the `commandcode` model provider is a documented GLOBAL dependency (global
  OpenCode plugin) rather than declared in-repo.
- [decision] 2026-09-10: OpenCode skill invocation is gated from the source
  flag. OpenCode ignores Claude's `disable-model-invocation` frontmatter and
  has no user-only skill invocation, so
  `opencode_engine.collect_disabled_skills()` reads `.kilo/skill/*/SKILL.md`
  and emits `permission.skill[name] = "ask"` (with `"*": "allow"` first) in the
  generated `opencode.json`. 10 skills carry the flag; no tooling previously
  consumed it. #2 done: deleted the unused `@opencode-ai/plugin` dep from the
  untracked `.opencode/package.json` + node_modules (local-only).
- [decision] 2026-09-11: harness-consistency audit (F1-F10); full write-up in
  `docs/audit-2026-09-11.md`. Policy call to carry forward: skill data assets
  (`.xml`) are allowed only inside a `skill*/` directory — NOT added to
  `boundary_audit.HARNESS_ALLOWED_EXTENSIONS`, because a global extension
  entry would blind the audit to a stray file anywhere in a harness dir, which
  is the leak it exists to catch. Second call: the root `.harness.lock` is a
  SUPERSET of what deploy ships (this repo IS the harness), so it declares
  `.agents` (Antigravity's local junction) via a new
  `deploy.LOCAL_ONLY_HARNESS_DIRS` set — deliberately NOT in
  `EXCLUSIVE_HARNESS_DIRS`, whose members are eligible for full stale-cleanup
  and a locally-created junction at a target is not safe to wipe. `DIRS_ALL`
  still never includes `.agents`. **This supersedes the `--bare`-default
  described in the 2026-08-06 entry**: every launcher profile runs full mode by
  default since 2026-08-08; `--bare` is explicit opt-in.
- [decision] 2026-09-14: Codex CLI added as a harness-consumer engine
  (NOT a harness mirror — Codex reads `AGENTS.md` natively, so no `.codex/`
  engine dir is generated). Installed `@openai/codex` 0.154.0 (npm, global).
  Added `codex-env.ps1` (launcher) and `tools/codex_usage.py` (metering).
  Four findings, each verified by experiment, that a future session must not
  re-derive:
  1. **Codex never reads `.env`.** It resolves the key from the env var named
     by `env_key` in `~/.codex/config.toml`, and its base URL is a static
     config value. `codex-env.ps1` therefore loads `.env`, exports
     `OPENAI_API_KEY`, and passes the URL via
     `-c model_providers.freemodel.base_url=...`.
  2. **`${VAR}` interpolation does NOT work in `base_url`** — setting
     `base_url = "${OPENAI_BASE_URL}/v1"` fails with "stream disconnected
     before completion: builder error". Hence the `-c` override above.
  3. **Codex's "code mode" must be OFF.** With it on, the model is asked to
     emit free-form JS (`const r = await tools.exec_command({...})`), which the
     gateway's models do not understand: they reply in prose, no tool ever
     runs, and the turn ends having done nothing. Fix is
     `[features] code_mode.enabled = false` + `unified_exec = false`. This
     looks identical to "provider lacks function calling", but it is not —
     calling `/v1/responses` directly with a `tools` array returns a proper
     `function_call` item, so the provider is fine and the wire format was the
     problem.
  4. **Windows sandbox blocks every shell command** ("rejected: blocked by
     policy") even under `workspace-write`, leaving the agent unable to run
     tests or git. Set `sandbox_mode = "danger-full-access"` +
     `approval_policy = "never"` (same trust model Claude Code/Kilo run under).
  Two smaller traps: `wire_api = "chat"` was **removed** in 0.154 (only
  `responses` remains), and TOML bare keys must precede the first `[table]`
  header — `sandbox_mode` placed after `[features]` lands inside it and Codex
  refuses to start.
- [decision] 2026-09-14: FreeModel gateway routing is NOT stable per model
  name — only `gpt-5.6-terra` is usable. This was measured objectively from
  API-side data (`usage.input_tokens` and the response's own `model` field),
  never by asking the model what it is. Method that produced the result:
  send one fixed 600-char string repeatedly and compare token counts; a stable
  backend returns identical counts and the same `model` id every time.
  Results: `gpt-5.6-terra` STABLE (150/150/150/150, and 150/181/94 for
  en/vi/code text across two passes each, always `served=gpt-5.6-terra`);
  `gpt-5.6-sol` UNSTABLE (150 vs 820 for identical text); `gpt-5.5` and
  `gpt-5.4` do not exist as distinct models — 4/4 requests for each were
  answered by `gpt-5.6-sol`, and both returned 150-vs-820 token spreads;
  `gpt-5.6-luna` is dead (HTTP 502 on 3 attempts spaced 5s apart).
  Tokenizer fingerprint for terra matches OpenAI's `o200k_base`
  (zh/en chars-per-token ratio 0.32; English 4.55 chars/token, Chinese 1.44,
  emoji 0.56), i.e. NOT a CJK-optimised tokenizer. Conclusion recorded for the
  pricing question: the gateway is a router over a pool ("routes each request
  to the best open model"), so "cheaper than buying direct" is not a
  like-for-like claim — the underlying model is anonymous and, for every alias
  except terra, changes between calls. Use terra for bulk mechanical work; do
  not use this gateway for work that needs reproducibility.
  **Measurement traps, do not repeat:** (a) asking the model to identify
  itself proves nothing; (b) four calls inside a few seconds do not
  demonstrate stability over time — vary the text and space the calls out
  (the sol/gpt-5.5 spread only shows up across repeats); (c) the response's
  `model` field is not a claim by the model, it is routing metadata, which is
  exactly why it is admissible evidence.
- [decision] 2026-09-14: Cost/metering path for Codex + FreeModel. FreeModel
  returns no cost field (its `/v1/responses` usage block carries tokens only,
  and `/api/billing` needs a browser session, not an API key), so
  `tools/codex_usage.py` computes cost from token counts times reference
  prices, and reads token/cache data from Codex's own rollout log —
  `~/.codex/sessions/**/rollout-*.jsonl`, event type `token_usage_record`,
  which breaks out `cached_input_tokens` per API call with `usage` /
  `turn_token_usage` / `thread_token_usage` variants. No extra Codex config is
  needed to get this data. Cached input is 10x cheaper ($0.2/M vs $2/M on
  terra), so cache hit rate is the dominant cost lever; long sessions hold
  cache (measured 40-47%), many short sessions do not (0%). Plan arithmetic:
  $20/month buys a $20 allowance per rolling 5h window capped at $132/week
  (~$572/month of list-price value), so break-even is $4.62/week of value.
  Terra list prices used: $2/M in, $12/M out, $0.2/M cached.
