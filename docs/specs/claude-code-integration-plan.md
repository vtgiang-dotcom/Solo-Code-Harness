# Claude Code — Full Engine Integration Plan

## Goal
Promote `.claude/` from a partial (agents-only) engine to a **first-class engine**
generated from `.kilo/` source, at parity with `.opencode` / `.copilot` / `.gemini`.

## Source of truth
`.kilo/` remains the single source. A new generator module produces `.claude/`.
Field `model` is dropped from generated agents → session default model is used.

## Deliverables

| # | Artifact | Path | Source |
|---|----------|------|--------|
| 1 | Root rulebook | `CLAUDE.md` | `AGENTS.md` + boundaries |
| 2 | Subagents (14) | `.claude/agents/*.md` | `.kilo/agents/` (frontmatter → Claude format) |
| 3 | Skills (47) | `.claude/skills/<name>/SKILL.md` | `.kilo/skill/` |
| 4 | Slash commands | `.claude/commands/*.md` | `.kilo/command/` |
| 5 | Guard hook | `.claude/hooks/guard.py` + `settings.json` | port of `solocode-guard.js` |
| 6 | Instructions (ref) | `.claude/instruction/*.md` | `.kilo/instruction/` |

## Frontmatter mapping: Kilo agent → Claude subagent

| Kilo field | Claude field | Rule |
|------------|--------------|------|
| `description` | `description` | copy verbatim |
| `mode: primary` | (none) | primary → user-invocable, no restriction |
| `mode: subagent` | (none) | still a subagent file |
| `permission.<tool>: allow/ask` | `tools:` allowlist | allow/ask → include tool; deny → exclude |
| `color`, `steps`, `variant` | (dropped) | not supported by Claude |
| `model` | (dropped) | use session default |

Tool name map: read→Read, edit→Edit(+Write), grep→Grep, glob→Glob, bash→Bash,
codesearch→(Grep), task→Task.

## Hooks (guard) — Claude Code PreToolUse
- `settings.json` registers a `PreToolUse` hook matching `Bash|Edit|Write`.
- `.claude/hooks/guard.py` reads tool_input JSON from stdin, applies the same
  BLOCK_PATTERNS / SECRET_PATTERNS / PROTECTED_FILES as `solocode-guard.js`,
  and blocks with exit code 2 (stderr feedback) — the Claude-native block path.
- Python (stdlib-only) chosen over jq/bash for Windows portability.

## Toolchain wiring
- `tools/claude_engine.py` — new module, all generation logic.
- `generate_harness.py` — call `generate_claude()` in `--harness all` + add `claude` choice.
- `garden.py` — add `.claude/` engine parity checks (skills/agents/commands/instructions).
- `deploy.py` — add `.claude`, `.claude-plugin`, `CLAUDE.md` to DIRS_ALL / files.
- `.harness.lock` — add `.claude`, `.claude-plugin`, `CLAUDE.md` to boundaries.

## Validation
`make generate && make garden && make validate && make check` all green.
