#!/usr/bin/env python3
"""
opencode_engine.py — OpenCode engine generator.

Reads .kilo/ (source of truth) and emits .opencode/ (agents, commands,
skills, instructions) plus root opencode.json.

History: .opencode/ was removed in v4.0.0 (it was then a 100%-content mirror
of .kilo/ with no unique capability, and OpenCode's format at the time was
in flux). It is reintroduced now (2026-08) as a first-class primary engine
alongside Claude Code, because Claude Code's gateway path has become
unreliable. OpenCode v1.18+ has a stable native format that Kilo's own
frontmatter already follows (Kilo was originally mirroring OpenCode), so the
transform is near-identity: we only drop tool keys OpenCode does not have.

Transform rules (source -> OpenCode):
  - agents:   .kilo/agents/*.md   -> .opencode/agents/*.md
              frontmatter kept as-is except: `codesearch` and `mcp`
              permission keys are dropped (OpenCode has no such tools; the
              remaining keys read/edit/grep/glob/bash/task are native).
  - commands: .kilo/command/*.md  -> .opencode/commands/*.md
              frontmatter kept as-is (description/mode/subtask/task).
  - skills:   .kilo/skill/<n>/SKILL.md -> .opencode/skills/<n>/SKILL.md
              copied verbatim; the skip list applies.
  - instructions: .kilo/instruction/*.md -> .opencode/instruction/*.md
              copied verbatim (byte-for-byte mirror, like .copilot/.gemini).
"""

from __future__ import annotations

import shutil
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
ROOT_DIR = TOOLS_DIR.parent

# Permission keys Kilo carries that OpenCode v1.18 has no equivalent tool for.
# Dropping them keeps the agent valid instead of silently mapping to nothing.
_DROP_PERMISSION_KEYS = {"codesearch", "mcp"}


def _normalize_agent_frontmatter(frontmatter: str) -> str:
    """Drop OpenCode-unknown permission keys from a Kilo agent frontmatter.

    The Kilo permission block uses 2-space indentation; top-level keys (mode,
    color, steps, description) sit at column 0, and `permission:` is a bare
    top-level key whose children are indented. We remove only the child lines
    whose key is in _DROP_PERMISSION_KEYS (and their own nested children).
    """
    out: list[str] = []
    in_dropped_key = False
    permission_indent: int | None = None
    for raw in frontmatter.split("\n"):
        stripped = raw.strip()
        if not stripped:
            out.append(raw)
            continue
        indent = len(raw) - len(raw.lstrip(" "))

        if permission_indent is None:
            # Look for the `permission:` header (bare key at any column).
            if stripped == "permission:":
                permission_indent = indent
                out.append(raw)
            else:
                out.append(raw)
            continue

        # Inside the permission block: a line at column <= permission_indent
        # that is not a child of the permission key ends the block.
        if indent <= permission_indent:
            permission_indent = None
            in_dropped_key = False
            out.append(raw)
            continue

        # Child lines belong to the permission block.
        if in_dropped_key:
            # Nested children of a dropped key are also dropped until dedent.
            if indent <= permission_indent + 2:
                in_dropped_key = False
                out.append(raw)
            # else: still inside the dropped key's children — skip
            continue

        key = stripped.split(":", 1)[0].strip().strip('"').strip("'")
        if key in _DROP_PERMISSION_KEYS:
            in_dropped_key = True
            continue
        out.append(raw)
    return "\n".join(out).rstrip("\n")


def generate_agents(kilo_root: Path, opencode_root: Path) -> int:
    src_dir = kilo_root / "agents"
    dst_dir = opencode_root / "agents"
    if not src_dir.is_dir():
        print(f"[ERROR] Source agent directory not found: {src_dir}")
        return 1
    dst_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for agent_file in sorted(src_dir.glob("*.md")):
        content = agent_file.read_text(encoding="utf-8")
        split = content.split("---", 2)
        if len(split) < 3:
            print(f"  [SKIP] agents/{agent_file.name} (no frontmatter)")
            continue
        fm = _normalize_agent_frontmatter(split[1].strip("\n"))
        body = split[2].lstrip("\n")
        new_content = f"---\n{fm}\n---\n{body}"
        (dst_dir / agent_file.name).write_text(new_content, encoding="utf-8", newline="")
        copied += 1
        print(f"  [GEN] agents/{agent_file.name}")
    print(f"OpenCode agents generated: {copied}")
    return 0


def generate_commands(kilo_root: Path, opencode_root: Path) -> int:
    src_dir = kilo_root / "command"
    dst_dir = opencode_root / "commands"
    if not src_dir.is_dir():
        print(f"[ERROR] Source command directory not found: {src_dir}")
        return 1
    dst_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for cmd_file in sorted(src_dir.glob("*.md")):
        content = cmd_file.read_text(encoding="utf-8")
        (dst_dir / cmd_file.name).write_text(content, encoding="utf-8", newline="")
        copied += 1
        print(f"  [GEN] commands/{cmd_file.name}")
    print(f"OpenCode commands generated: {copied}")
    return 0


def generate_skills(
    kilo_root: Path, opencode_root: Path, *, skip_names: set[str] | None = None
) -> int:
    src_dir = kilo_root / "skill"
    dst_dir = opencode_root / "skills"
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
    print(f"OpenCode skills generated: {copied}")
    return 0


def generate_instructions(kilo_root: Path, opencode_root: Path) -> int:
    src_dir = kilo_root / "instruction"
    dst_dir = opencode_root / "instruction"
    if not src_dir.is_dir():
        print(f"[ERROR] Source instruction directory not found: {src_dir}")
        return 1
    dst_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for f in sorted(src_dir.glob("*.md")):
        dst = dst_dir / f.name
        dst.write_bytes(f.read_bytes())
        copied += 1
    print(f"OpenCode instructions copied: {copied}")
    return 0


def generate_opencode_json(opencode_root: Path, root_dir: Path) -> int:
    """Write root opencode.json (model default + native permission guard).

    Permission system is OpenCode's native guard, chosen over porting the old
    solocode-guard.js plugin. It denies destructive bash/editor patterns the
    same way the Kilo/Claude hooks do, and keeps the project's own gates
    (security_scan/checklist) always-allowed.
    """
    content = """{
  "$schema": "https://opencode.ai/config.json",
  "model": "commandcode/deepseek-v4-pro",
  "small_model": "commandcode/gpt-5.4-mini",
  "default_agent": "solo-code-engineer",
  "instructions": [
    "AGENTS.md",
    ".opencode/instruction/*.md"
  ],
  "agent": {
    "solo-code-engineer": {
      "model": "commandcode/deepseek-v4-pro"
    }
  },
  "permission": {
    "edit": "ask",
    "bash": {
      "*": "ask",
      "python .github/scripts/security_scan.py *": "allow",
      "python .github/scripts/checklist.py *": "allow",
      "git status*": "allow",
      "git diff*": "allow",
      "git log*": "allow",
      "git add*": "allow",
      "git commit*": "allow",
      "git push*": "ask",
      "git reset --hard*": "deny",
      "git push --force*": "deny",
      "rm -rf *": "deny",
      "rm -rf /*": "deny",
      "del /s /q *": "deny",
      "DROP TABLE*": "deny",
      "DROP DATABASE*": "deny"
    },
    "external_directory": "ask"
  }
}
"""
    dst = root_dir / "opencode.json"
    dst.write_text(content, encoding="utf-8", newline="")
    print("OpenCode config generated: opencode.json")
    return 0


def generate_all(
    kilo_root: Path, opencode_root: Path, root_dir: Path, *, skip_names: set[str] | None = None
) -> int:
    opencode_root.mkdir(parents=True, exist_ok=True)
    print("--- OpenCode agents ---")
    if generate_agents(kilo_root, opencode_root) != 0:
        return 1
    print("--- OpenCode commands ---")
    generate_commands(kilo_root, opencode_root)
    print("--- OpenCode skills ---")
    generate_skills(kilo_root, opencode_root, skip_names=skip_names)
    print("--- OpenCode instructions ---")
    generate_instructions(kilo_root, opencode_root)
    print("--- OpenCode config ---")
    generate_opencode_json(opencode_root, root_dir)
    return 0
