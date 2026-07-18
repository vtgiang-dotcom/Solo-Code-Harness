#!/usr/bin/env python3
"""
Solo-Code -> Claude Code Engine Generator

Reads .kilo/ source assets and replicates them into .claude/ for Claude Code,
making Claude a first-class engine at parity with .opencode / .copilot / .gemini.

Generated artifacts:
  - .claude/agents/*.md          Subagents (Kilo permission -> Claude tools allowlist)
  - .claude/skills/<n>/SKILL.md  Skills (copied verbatim; format is compatible)
  - .claude/commands/*.md        Slash commands (frontmatter normalized)
  - .claude/instruction/*.md     Instruction references (copied verbatim)
  - CLAUDE.md                    Root rulebook (generated from AGENTS.md + boundaries)

Design notes:
  - The `model` field is intentionally dropped from agents so Claude uses the
    session default model (works with any provider/gateway).
  - Static hook infra (.claude/hooks/*.py, .claude/settings.json) is NOT
    generated here -- it is version-controlled static harness code. This covers
    the PreToolUse guard plus the PostToolUse (quality_gate, security_post) and
    SessionStart/SessionEnd lifecycle hooks.

Usage (via generate_harness.py):
    python tools/generate_harness.py --harness claude
    python tools/generate_harness.py --harness all
"""

from __future__ import annotations

import contextlib
import re
import shutil
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
ROOT_DIR = TOOLS_DIR.parent

NL = "\n"

# Kilo permission tool -> Claude Code tool name(s).
# `edit` maps to both Edit and Write (Claude splits file mutation into two tools).
# `codesearch` has no Claude equivalent -> folds into Grep.
# `task` -> Task (subagent delegation).
_TOOL_MAP: dict[str, list[str]] = {
    "read": ["Read"],
    "edit": ["Edit", "Write"],
    "grep": ["Grep"],
    "glob": ["Glob"],
    "codesearch": ["Grep"],
    "bash": ["Bash"],
    "task": ["Task"],
}

# Deterministic ordering for the generated tools: [...] allowlist.
_TOOL_ORDER = ["Read", "Grep", "Glob", "Edit", "Write", "Bash", "Task"]


# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------

def _split_frontmatter(content: str) -> tuple[str, str] | None:
    """Return (frontmatter, body) or None if no valid frontmatter block."""
    if not content.startswith("---"):
        return None
    end = content.find("\n---", 3)
    if end == -1:
        return None
    frontmatter = content[3:end].strip("\n")
    body = content[end + 4:]
    return frontmatter, body


def _parse_kilo_permissions(frontmatter: str) -> tuple[dict[str, str], str, str | None]:
    """Parse a Kilo agent frontmatter permission block.

    Returns:
      perms:       {tool: effect} where effect is the *most permissive* seen
                   ("allow" > "ask" > "deny") across nested patterns.
      description: agent description (unquoted).
      mode:        "primary" | "subagent" | None.
    """
    lines = frontmatter.split("\n")
    perms: dict[str, str] = {}
    description = ""
    mode: str | None = None

    in_perm = False
    perm_indent = 0
    current_tool: str | None = None

    rank = {"deny": 0, "ask": 1, "allow": 2}

    def record(tool: str, effect: str) -> None:
        effect = effect.strip().strip('"').strip("'")
        if effect not in rank:
            return
        prev = perms.get(tool)
        if prev is None or rank[effect] > rank[prev]:
            perms[tool] = effect

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        indent = len(line) - len(line.lstrip(" "))

        # Top-level keys
        if not in_perm:
            if stripped.startswith("description:"):
                description = stripped.split(":", 1)[1].strip().strip('"').strip("'")
                continue
            if stripped.startswith("mode:"):
                mode = stripped.split(":", 1)[1].strip()
                continue
            if re.match(r"^permission:\s*$", stripped):
                in_perm = True
                perm_indent = indent
                current_tool = None
                continue
            continue

        # Inside permission block -- detect end (dedent with a new top-level key)
        if indent <= perm_indent and ":" in stripped and not stripped.startswith('"') and not stripped.startswith("'"):
            in_perm = False
            current_tool = None
            if stripped.startswith("description:"):
                description = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            elif stripped.startswith("mode:"):
                mode = stripped.split(":", 1)[1].strip()
            continue

        # Tool-level entry: "  tool: effect" or "  tool:"
        m = re.match(r'^([\w*"\'.-]+):\s*(\S.*)?$', stripped)
        if m and indent == perm_indent + 2:
            tool = m.group(1).strip('"').strip("'")
            val = m.group(2)
            current_tool = tool
            if val:
                record(tool, val)
            continue

        # Nested pattern entry: '    "pattern": effect'
        sm = re.match(r'^(.+?):\s*(\S+)\s*$', stripped)
        if sm and current_tool and indent >= perm_indent + 4:
            record(current_tool, sm.group(2))
            continue

    return perms, description, mode


def _build_tools_allowlist(perms: dict[str, str]) -> list[str]:
    """Map Kilo permissions to a deterministic Claude tools allowlist.

    A tool is included if its effect is allow or ask (deny -> excluded).
    """
    allowed: set[str] = set()
    for tool, effect in perms.items():
        if effect in ("allow", "ask"):
            for claude_tool in _TOOL_MAP.get(tool, []):
                allowed.add(claude_tool)
    return [t for t in _TOOL_ORDER if t in allowed]


def _derive_description(name: str) -> str:
    return " ".join(w.capitalize() if i == 0 else w for i, w in enumerate(name.replace("-", " ").split()))


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

def generate_agents(kilo_root: Path, claude_root: Path) -> int:
    """Generate .claude/agents/*.md from .kilo/agents/*.md."""
    src_dir = kilo_root / "agents"
    dst_dir = claude_root / "agents"
    if not src_dir.is_dir():
        print(f"[ERROR] Source agent directory not found: {src_dir}")
        return 1

    dst_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for agent_file in sorted(src_dir.glob("*.md")):
        name = agent_file.stem
        content = agent_file.read_text(encoding="utf-8")
        split = _split_frontmatter(content)
        if split is None:
            print(f"  [SKIP] {name} (no frontmatter)")
            continue
        frontmatter, body = split
        perms, description, _mode = _parse_kilo_permissions(frontmatter)
        if not description:
            description = _derive_description(name)
        tools = _build_tools_allowlist(perms)

        fm = f"name: {name}{NL}description: {description}{NL}"
        if tools:
            fm += f"tools: {', '.join(tools)}{NL}"
        # `model` intentionally omitted -> session default model.

        new_content = f"---{NL}{fm}---{NL}{body.lstrip(NL)}"
        (dst_dir / agent_file.name).write_text(new_content, encoding="utf-8")
        copied += 1
        print(f"  [GEN] agents/{agent_file.name}  tools=[{', '.join(tools) or 'inherit'}]")

    print(f"Claude agents generated: {copied}")
    return 0


def generate_skills(kilo_root: Path, claude_root: Path, *, skip_names: set[str] | None = None) -> int:
    """Copy skills from .kilo/skill/ to .claude/skills/ (Claude uses plural 'skills')."""
    src_dir = kilo_root / "skill"
    dst_dir = claude_root / "skills"
    if not src_dir.is_dir():
        print(f"[ERROR] Source skill directory not found: {src_dir}")
        return 1

    skip_names = skip_names or set()
    dst_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for skill_dir in sorted(p for p in src_dir.iterdir() if p.is_dir()):
        name = skill_dir.name
        if name in skip_names:
            print(f"  [SKIP] skills/{name} (skip list)")
            continue
        if not (skill_dir / "SKILL.md").is_file():
            print(f"  [SKIP] skills/{name} (no SKILL.md)")
            continue
        dest = dst_dir / name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(skill_dir, dest)
        copied += 1
    print(f"Claude skills generated: {copied}")
    return 0


def generate_commands(kilo_root: Path, claude_root: Path) -> int:
    """Generate .claude/commands/*.md from .kilo/command/*.md.

    Kilo commands use `subtask: true`; Claude uses standard slash-command
    frontmatter (description + optional argument-hint). We keep description and
    drop Kilo-specific keys.
    """
    src_dir = kilo_root / "command"
    dst_dir = claude_root / "commands"
    if not src_dir.is_dir():
        print(f"[ERROR] Source command directory not found: {src_dir}")
        return 1

    dst_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for cmd_file in sorted(src_dir.glob("*.md")):
        content = cmd_file.read_text(encoding="utf-8")
        split = _split_frontmatter(content)
        if split is None:
            desc = _derive_description(cmd_file.stem)
            new_content = f"---{NL}description: {desc}{NL}---{NL}{content}"
        else:
            frontmatter, body = split
            description = ""
            for line in frontmatter.split("\n"):
                s = line.strip()
                if s.startswith("description:"):
                    description = s.split(":", 1)[1].strip().strip('"').strip("'")
                    break
            if not description:
                description = _derive_description(cmd_file.stem)
            new_content = f"---{NL}description: {description}{NL}---{NL}{body.lstrip(NL)}"
        (dst_dir / cmd_file.name).write_text(new_content, encoding="utf-8")
        copied += 1
        print(f"  [GEN] commands/{cmd_file.name}")
    print(f"Claude commands generated: {copied}")
    return 0


def generate_instructions(kilo_root: Path, claude_root: Path) -> int:
    """Copy instruction files verbatim to .claude/instruction/ for reference."""
    src_dir = kilo_root / "instruction"
    dst_dir = claude_root / "instruction"
    if not src_dir.is_dir():
        print(f"[ERROR] Source instruction directory not found: {src_dir}")
        return 1

    dst_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for f in sorted(src_dir.glob("*.md")):
        dst = dst_dir / f.name
        dst.write_bytes(f.read_bytes())
        with contextlib.suppress(Exception):
            shutil.copystat(f, dst)
        copied += 1
    print(f"Claude instructions copied: {copied}")
    return 0


def generate_memory(kilo_root: Path, claude_root: Path) -> int:
    """Copy memory files from .kilo/memory/ to .claude/memory/ for parity.

    Claude Code auto-loads CLAUDE.md as primary memory, but mirroring the
    .kilo/memory/ corpus (MEMORY.md index, conventions, design intent) keeps the
    knowledge available to subagents and prevents cross-engine drift (feat-008).
    """
    src_dir = kilo_root / "memory"
    dst_dir = claude_root / "memory"
    if not src_dir.is_dir():
        print(f"[ERROR] Source memory directory not found: {src_dir}")
        return 1

    dst_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for f in sorted(src_dir.glob("*.md")):
        dst = dst_dir / f.name
        dst.write_bytes(f.read_bytes())
        with contextlib.suppress(Exception):
            shutil.copystat(f, dst)
        copied += 1
    print(f"Claude memory copied: {copied}")
    return 0


def generate_claude_md(root_dir: Path) -> int:
    """Generate root CLAUDE.md -- Claude Code auto-loads this as project memory."""
    agents_dir = root_dir / ".kilo" / "agents"
    skills_dir = root_dir / ".kilo" / "skill"
    commands_dir = root_dir / ".kilo" / "command"
    n_agents = len(list(agents_dir.glob("*.md"))) if agents_dir.is_dir() else 0
    n_skills = len([p for p in skills_dir.iterdir() if p.is_dir()]) if skills_dir.is_dir() else 0
    n_commands = len(list(commands_dir.glob("*.md"))) if commands_dir.is_dir() else 0

    content = _CLAUDE_MD_TEMPLATE.format(
        n_agents=n_agents, n_skills=n_skills, n_commands=n_commands
    )
    (root_dir / "CLAUDE.md").write_text(content, encoding="utf-8")
    print("Claude rulebook generated: CLAUDE.md")
    return 0


_CLAUDE_MD_TEMPLATE = """<!-- GENERATED by tools/claude_engine.py from .kilo/ source. Do not edit by hand. -->
# Solo-Code Harness -- Claude Code Rulebook

Claude Code auto-loads this file as project memory. It mirrors `AGENTS.md`
(the cross-engine root rulebook) for the Claude engine. Source of truth is
`.kilo/`; regenerate with `python tools/generate_harness.py --harness claude`.

## Harness Boundaries (READ FIRST)

> **DO NOT CONFUSE harness files with project source code.**

Before analyzing or modifying ANY file, classify it:

| If the path starts with... | Then it is... | Action |
|----------------------------|---------------|--------|
| `.kilo/`, `.opencode/`, `.copilot/`, `.gemini/`, `.claude/` | Harness engine | AI behavior config -- not project logic |
| `.vscode/` | Harness IDE config | Editor + MCP config -- not project source |
| `.github/scripts/` | Harness verification | Security/lint/eval scripts |
| `tools/` | Harness utilities | Generator, deploy, garden, config |
| `.contracts/` | Sub-agent contracts | Status contracts for delegated agents |
| `AGENTS.md`, `CLAUDE.md`, `agent.yaml`, `kilo.jsonc`, `opencode.json`, `.mcp.json`, `Makefile`, `SPEC.md`, `.harness.lock`, `.solocode/` | Harness config | Agent behavior config -- not app config |
| **Everything else** | **Project code** | Your actual application -- this is what you modify |

**Key rule:** Never modify harness files to fix a project bug, and never modify
project files to fix a harness issue. Read `.harness.lock` for the authoritative
boundary list.

## Self-Verification Handshake

When asked "Is Solo-Code Harness active?", answer:
`Solo-Code Harness active: behavior rules, anti-hallucination rules, security rules,
prose quality rules, {n_skills} skills, {n_agents} agents, guard + lifecycle hooks enabled (Claude Code).
Use /verify to validate.`

## Claude Code Assets

- **Subagents ({n_agents})** in `.claude/agents/` -- invoke via the Task tool or by name.
- **Skills ({n_skills})** in `.claude/skills/` -- auto-discovered `SKILL.md` capabilities.
- **Slash commands ({n_commands})** in `.claude/commands/` -- `/verify`, `/plan`, `/decide`, `/ship`, and more.
- **Guard hook** in `.claude/hooks/guard.py` (`PreToolUse`) -- blocks destructive
  commands, secret leaks, and protected-config edits.
- **Quality-gate hook** in `.claude/hooks/quality_gate.py` (`PostToolUse` Edit/Write)
  -- advisory format check (ruff/prettier/biome/gofmt) after each edit.
- **Security-post hook** in `.claude/hooks/security_post.py` (`PostToolUse` Bash)
  -- scans `git diff` for secrets after `git commit`/`git push`.
- **Session hooks** `session_start.py` / `session_end.py` (`SessionStart`/`SessionEnd`)
  -- load git + cross-engine context at start; log the session to the local
  shared-state DB at end. All hooks are stdlib-only Python and non-blocking except the guard.

## Behavior Rules (MANDATORY)

### Safety
- Never run destructive commands (`rm -rf`, `git reset --hard`, `git push --force` to main/master, `DROP TABLE`) without explicit user confirmation. The guard hook blocks these by default.
- Never commit secrets. The guard hook scans commands and edits for credentials.
- Never edit protected linter/formatter config (`.ruff.toml`, `eslint.config.js`, etc.) without asking.

### Code Quality
- Make surgical changes -- touch only what the task requires.
- Prefer fixing root causes over symptoms.
- Match existing conventions (naming, structure, style) in the file you edit.

### AI Discipline (Anti-Hallucination)
- Verify before claiming. Do not say a change works until you have run it.
- Read a file before editing it. Do not invent APIs, flags, or file paths.
- Prefer fresh information -- re-read files that may have changed.

### Prose Quality
- Be concise and specific. No filler, no hedging, no marketing tone.

## Security Rules
- Validate and sanitize all external input.
- Never log secrets or PII.
- Use parameterized queries -- never string-concatenate SQL.
- Keep credentials in environment variables, never in source.

## Verification Gates
Run `/verify` (or `make check`) before declaring work complete:
1. `ruff check .` -- Python lint
2. `python tools/validate_schemas.py` -- frontmatter schema validation
3. `python tools/garden.py` -- cross-engine parity / drift detection
4. `python -m pytest tools/test_harness.py -q` -- generator tests
5. `python .github/scripts/security_scan.py .` -- secret scan

## Git Commit Convention
Use Conventional Commits: `type(scope): summary` (feat, fix, docs, test, refactor, chore).

## Language
Respond in the user's language. Code, identifiers, and commit messages stay in English.
"""


def generate_all(kilo_root: Path, claude_root: Path, root_dir: Path, *, skip_names: set[str] | None = None) -> int:
    """Generate every Claude engine artifact. Returns 0 on success."""
    claude_root.mkdir(parents=True, exist_ok=True)
    print("--- Claude agents ---")
    ec = generate_agents(kilo_root, claude_root)
    if ec != 0:
        return ec
    print("--- Claude skills ---")
    generate_skills(kilo_root, claude_root, skip_names=skip_names)
    print("--- Claude commands ---")
    generate_commands(kilo_root, claude_root)
    print("--- Claude instructions ---")
    generate_instructions(kilo_root, claude_root)
    print("--- Claude memory ---")
    generate_memory(kilo_root, claude_root)
    print("--- Claude rulebook ---")
    generate_claude_md(root_dir)
    return 0
