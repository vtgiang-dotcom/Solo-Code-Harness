#!/usr/bin/env python3
"""
Solo-Code → OpenCode Harness Generator

Reads .kilo/ assets and replicates them into .opencode/ for OpenCode.

Phases:
  Phase 1 — Skills (37 portable, 5 skipped)
  Phase 2 — Agents (14, with permission V1→V2 migration)
  Phase 3 — Instructions (7, copy + rename → .instructions.md; optional --global-install)
  Phase 4 — Memory (3, copy for preservation)

Usage:
    python tools/generate_harness.py --harness all
    python tools/generate_harness.py --harness all --plugin X
    python tools/generate_harness.py --harness all --include-all
    python tools/generate_harness.py --harness all --global-install
    python tools/generate_harness.py --harness agents
"""

from __future__ import annotations

import argparse
import contextlib
import re
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths — resolved relative to this script's location
# ---------------------------------------------------------------------------

TOOLS_DIR = Path(__file__).resolve().parent
ROOT_DIR = TOOLS_DIR.parent
SKIP_FILE = TOOLS_DIR / "opencode-skip-skills.txt"
KILO_DIR = ROOT_DIR / ".kilo"
OPENCODE_DIR = ROOT_DIR / ".opencode"
CLAUDE_DIR = ROOT_DIR / ".claude"


def _load_claude_engine():
    """Import the sibling claude_engine module (tools/ may not be on sys.path)."""
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    import claude_engine
    return claude_engine


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def load_skip_list(skip_file: Path) -> set[str]:
    """Read skill names to skip (one per line). Returns empty set on error."""
    if not skip_file.is_file():
        print(f"[WARN] Skip file not found: {skip_file}")
        print("[WARN]  -> All 42 skills will be copied.")
        return set()
    names = {line.strip() for line in skip_file.read_text(encoding="utf-8").splitlines() if line.strip()}
    print(f"[INFO] Loaded {len(names)} skip entries from {skip_file.name}")
    for n in sorted(names):
        print(f"       - {n}")
    return names


def copy_dir(src: Path, dst: Path, opencode_root: Path) -> None:
    """Copy a directory tree. Idempotent + safety guard against stray paths."""
    try:
        dst.relative_to(opencode_root)
    except ValueError:
        print(f"  [FAIL] Refusing to rmtree {dst} — not inside {opencode_root}")
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def copy_file(src: Path, dst: Path) -> None:
    """Copy a single file, creating parent directories.

    Uses binary read/write to avoid Unicode encoding issues on Windows
    when source files contain characters outside the system codepage
    (e.g. right-arrow U+2192 in instruction files).
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    data = src.read_bytes()
    dst.write_bytes(data)
    # Preserve mtime if possible
    with contextlib.suppress(Exception):
        shutil.copystat(src, dst)


# ---------------------------------------------------------------------------
# Permission migration: Kilo V1 object → OpenCode V2 array
# ---------------------------------------------------------------------------

# Reference: opencode-dev/packages/core/src/v1/config/migrate.ts:75-92

def _migrate_value(action: str, raw_value: object) -> list[dict[str, str]]:
    """
    Convert a single V1 permission entry to V2 rules.

    Dạng 1: "read": "allow"
      → [{"action": "read", "resource": "*", "effect": "allow"}]

    Dạng 2: "bash": {"*": "ask", "git *": "allow"}
      → [{"action": "bash", "resource": "*", "effect": "ask"},
          {"action": "bash", "resource": "git *", "effect": "allow"}]
    """
    rules: list[dict[str, str]] = []

    if isinstance(raw_value, str):
        # Dạng 1: cấp 1 trực tiếp
        rules.append({"action": action, "resource": "*", "effect": raw_value})
    elif isinstance(raw_value, dict):
        # Dạng 2: cấp 2 có pattern
        for pattern, effect in raw_value.items():
            if isinstance(pattern, str) and isinstance(effect, str):
                rules.append({"action": action, "resource": pattern, "effect": effect})
    else:
        # Unknown type — skip
        pass

    return rules


def migrate_permission(frontmatter: str) -> str:
    """
    Parse frontmatter YAML, find `permission:` key, migrate to `permissions:`
    (V2 array format). Return the updated frontmatter string.

    This is a line-based YAML parser (no pyyaml dependency).
    Handles:
      permission:
        tool: "action"              # Dạng 1
        tool:
          "pattern": "action"       # Dạng 2
    """
    lines = frontmatter.split("\n")
    result: list[str] = []
    in_permission = False
    indent_level = 0
    collected_tools: list[tuple[int, str, object]] = []  # (line_index, action, raw_value)

    i = 0
    while i < len(lines):
        line = lines[i]

        # Detect "permission:" key
        m = re.match(r"^(\s*)permission:\s*$", line)
        if m:
            in_permission = True
            indent_level = len(m.group(1))
            # Collect all nested lines, then process
            i += 1
            raw_lines: list[str] = []
            while i < len(lines):
                next_line = lines[i]
                if re.match(r"^\s{0," + str(indent_level) + r"}\S", next_line) and not re.match(r"^\s{" + str(indent_level + 1) + r"}", next_line):
                    # Back to parent-level key — stop collecting
                    break
                raw_lines.append(next_line)
                i += 1
            # Parse collected permission block
            # Parse tool-level entries
            tool_key = None
            tool_value: str | dict | None = None
            tool_indent = indent_level + 2
            sub_indent = tool_indent + 2

            for rline in raw_lines:
                # Tool-level: "  tool: string" or "  tool:"
                tm = re.match(r"^(\s{2})(\S+):\s*(\S+)?\s*$", rline)
                if tm and len(tm.group(1)) == tool_indent:
                    # Flush previous tool
                    if tool_key is not None and tool_value is not None:
                        collected_tools.append((tool_key, tool_value, sub_indent))
                    tool_key = tm.group(2)
                    tool_value = tm.group(3) or {}
                    continue

                # Sub-entry: "    pattern: action"
                sm = re.match(r"^(\s{4})(\S+):\s+(\S+)", rline)
                if sm and tool_key and isinstance(tool_value, dict):
                    tool_value[sm.group(2)] = sm.group(3)
                    continue

            # Flush last tool
            if tool_key is not None and tool_value is not None:
                collected_tools.append((tool_key, tool_value, sub_indent))

            # Generate V2 permissions block
            all_rules: list[dict[str, str]] = []
            for action, raw_val, _ in collected_tools:
                all_rules.extend(_migrate_value(action, raw_val))

            pad = " " * indent_level
            item_pad = " " * (indent_level + 4)
            result.append(f"{pad}permissions:")
            for rule in all_rules:
                resource = rule["resource"]
                # YAML: * is an alias node character (special), must be quoted
                if resource in ("*", "?", "true", "false", "yes", "no", "on", "off", "null"):
                    resource = f'"{resource}"'
                result.append(
                    f"{item_pad}- action: {rule['action']}\n"
                    f"{item_pad}  resource: {resource}\n"
                    f"{item_pad}  effect: {rule['effect']}"
                )
            in_permission = False
            continue

        # Skip old permission key lines that were already replaced
        if in_permission:
            # Already handled above via the collected lines loop
            pass
        else:
            result.append(line)

        i += 1

    return "\n".join(result)


# ---------------------------------------------------------------------------
# Phase 1: Skills
# ---------------------------------------------------------------------------

def generate_skills(
    kilo_root: Path,
    opencode_root: Path,
    *,
    include_all: bool = False,
    plugin_filter: str | None = None,
) -> int:
    """Copy portable skills from .kilo/skill/ to .opencode/skill/."""
    src_dir = kilo_root / "skill"
    dst_dir = opencode_root / "skill"

    if not src_dir.is_dir():
        print(f"[ERROR] Source skill directory not found: {src_dir}")
        return 1

    skip_names: set[str] = set()
    if not include_all:
        skip_names = load_skip_list(SKIP_FILE)

    skills = sorted([entry for entry in src_dir.iterdir() if entry.is_dir()])

    copied: list[str] = []
    skipped: list[str] = []

    for skill_dir in skills:
        name = skill_dir.name
        skill_md = skill_dir / "SKILL.md"

        if not skill_md.is_file():
            print(f"  [SKIP] {name}  (no SKILL.md — not a valid skill)")
            continue

        if plugin_filter is not None and name != plugin_filter:
            continue

        if plugin_filter is None and name in skip_names:
            skipped.append(name)
            print(f"  [SKIP] {name}  (in skip list)")
            continue

        dest = dst_dir / name
        try:
            copy_dir(skill_dir, dest, opencode_root)
            copied.append(name)
            print(f"  [COPY] {name}")
        except Exception as exc:
            print(f"  [FAIL] {name}  ({exc})")

    print()
    print(f"Skills copied: {len(copied)}")
    if copied:
        print("  " + ", ".join(copied))
    if skipped:
        print(f"Skills skipped (blocklist): {len(skipped)}")
        print("  " + ", ".join(skipped))
    if plugin_filter and plugin_filter not in [s.name for s in skills]:
        print(f"[WARN] Plugin '{plugin_filter}' not found in skill directory.")
    return 0


# ---------------------------------------------------------------------------
# Phase 2: Agents
# ---------------------------------------------------------------------------

# Reasoning effort variant per agent role.
# OpenCode passes this as `variant` in the model request.
# Supported values: low, medium, high, max (model-dependent).
# Source: opencode-dev/packages/opencode/src/provider/transform.ts:859-862
AGENT_VARIANTS: dict[str, str] = {
    "architect": "high",
    "code-reviewer": "high",
    "code-simplifier": "low",
    "code-skeptic": "medium",
    "database-reviewer": "medium",
    "planner": "high",
    "python-reviewer": "high",
    "refactor-cleaner": "medium",
    "security-auditor": "high",
    "solo-code-engineer": "high",
    "tdd-guide": "medium",
    "test-engineer": "medium",
    "typescript-reviewer": "high",
    "web-performance-auditor": "medium",
}


def _inject_variant(frontmatter: str, name: str) -> str:
    """Inject `variant: X` line after the first frontmatter line (or after
    `mode:` if present), but skip if `variant:` already exists."""
    variant = AGENT_VARIANTS.get(name)
    if variant is None:
        return frontmatter

    lines = frontmatter.split("\n")
    for line in lines:
        if line.strip().startswith("variant:"):
            return frontmatter  # already set, don't override

    # Insert after `mode:` line, or after the first line
    insert_after = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("mode:"):
            insert_after = i
            break

    lines.insert(insert_after + 1, f"variant: {variant}")
    return "\n".join(lines)

def generate_agents(kilo_root: Path, opencode_root: Path) -> int:
    """Copy agents from .kilo/agents/ to .opencode/agents/ with permission
    V1→V2 migration."""
    src_dir = kilo_root / "agents"
    dst_dir = opencode_root / "agents"

    if not src_dir.is_dir():
        print(f"[ERROR] Source agent directory not found: {src_dir}")
        return 1

    agents = sorted([entry for entry in src_dir.iterdir() if entry.suffix == ".md"])

    copied: list[str] = []
    failed: list[str] = []

    for agent_file in agents:
        name = agent_file.stem
        print(f"  [PROC] {name}")

        try:
            content = agent_file.read_text(encoding="utf-8")

            # Split frontmatter from body
            # Frontmatter is between --- markers
            if not content.startswith("---"):
                print(f"  [SKIP] {name}  (no frontmatter)")
                continue

            # Find closing ---
            end_marker = content.find("\n---", 3)
            if end_marker == -1:
                print(f"  [SKIP] {name}  (malformed frontmatter)")
                continue

            frontmatter = content[3:end_marker]  # excluding the opening ---
            body = content[end_marker + 4:]  # after closing ---

            # Migrate permission
            migrated_fm = migrate_permission(frontmatter)

            # Inject variant (reasoning effort) based on agent role
            migrated_fm = _inject_variant(migrated_fm, name)

            # Reassemble (ensure trailing newline before closing ---)
            new_content = f"---{migrated_fm}\n---{body}"

            # Write
            dst = dst_dir / agent_file.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(new_content, encoding="utf-8")
            copied.append(name)
            print(f"  [COPY] {name}")

        except Exception as exc:
            failed.append(name)
            print(f"  [FAIL] {name}  ({exc})")

    print()
    print(f"Agents copied: {len(copied)}")
    if copied:
        print("  " + ", ".join(copied))
    if failed:
        print(f"Agents failed: {len(failed)}")
        print("  " + ", ".join(failed))
    return 0 if not failed else 1


# ---------------------------------------------------------------------------
# Phase 3: Instructions (copy + rename → .instructions.md for auto-load)
# ---------------------------------------------------------------------------

# OpenCode auto-loads every file matching *.instructions.md from
# ~/.agents/instructions/ (env.AGENTS_DIR or default ~/.agents).
# No opencode.json declaration needed for these files.
# Source: opencode-dev/packages/core/src/config.ts:74-78

AGENTS_DIR = Path.home() / ".agents"


def _instructions_rename(name: str) -> str:
    """Rename to *.instructions.md if not already."""
    if name.endswith(".instructions.md"):
        return name
    stem = Path(name).stem  # removes .md
    return f"{stem}.instructions.md"


def generate_instructions(
    kilo_root: Path,
    opencode_root: Path,
    *,
    global_install: bool = False,
) -> int:
    """Copy instruction files from .kilo/instruction/ to .opencode/instruction/
    with .instructions.md suffix for OpenCode auto-load.

    When global_install=True, also copy to ~/.agents/instructions/.
    """
    src_dir = kilo_root / "instruction"
    dst_dir = opencode_root / "instruction"

    if not src_dir.is_dir():
        print(f"[ERROR] Source instruction directory not found: {src_dir}")
        return 1

    files = sorted([entry for entry in src_dir.iterdir() if entry.is_file()])

    copied: list[str] = []

    for f in files:
        src_name = f.name
        dst_name = _instructions_rename(src_name)
        try:
            # Copy to .opencode/instruction/
            dst = dst_dir / dst_name
            copy_file(f, dst)
            copied.append(dst_name)
            print(f"  [COPY] {src_name} -> {dst_name}")

            # Optional: copy to global agents directory
            if global_install:
                global_dir = AGENTS_DIR / "instructions"
                global_dir.mkdir(parents=True, exist_ok=True)
                global_dst = global_dir / dst_name
                copy_file(f, global_dst)
                print(f"  [GLOBAL] {dst_name} -> {global_dst}")
        except Exception as exc:
            print(f"  [FAIL] {src_name}  ({exc})")

    print()
    print(f"Instructions copied: {len(copied)}")
    print("[INFO] OpenCode auto-loads *.instructions.md from ~/.agents/instructions/")
    print("[INFO] No opencode.json declaration needed.")

    # Print global install guide if not already installed
    if not global_install:
        print()
        print("=" * 60)
        print(" GLOBAL INSTALL GUIDE")
        print("=" * 60)
        print("  Run with --global-install to copy to:")
        print(f"    {AGENTS_DIR / 'instructions' / ''}")
        print()
        print("  Or manually:")
        for name in copied:
            print(f"    cp {dst_dir / name} {AGENTS_DIR / 'instructions' / name}")
        print("=" * 60)

    return 0


# ---------------------------------------------------------------------------
# Phase 4: Memory (copy for preservation — OpenCode has no memory system)
# ---------------------------------------------------------------------------

def generate_memory(kilo_root: Path, opencode_root: Path) -> int:
    """Copy memory files from .kilo/memory/ to .opencode/memory/.

    Note: OpenCode does not have an auto-loaded memory system equivalent
    to Kilo's MEMORY.md. These files are copied for preservation and
    can be loaded via references or instructions if needed.
    """
    src_dir = kilo_root / "memory"
    dst_dir = opencode_root / "memory"

    if not src_dir.is_dir():
        print(f"[ERROR] Source memory directory not found: {src_dir}")
        return 1

    files = sorted([entry for entry in src_dir.iterdir() if entry.is_file()])

    copied: list[str] = []

    for f in files:
        name = f.name
        try:
            dst = dst_dir / name
            copy_file(f, dst)
            copied.append(name)
            print(f"  [COPY] {name}")
        except Exception as exc:
            print(f"  [FAIL] {name}  ({exc})")

    print()
    print(f"Memory files copied: {len(copied)}")
    print("[NOTE] OpenCode does not auto-load memory. Files preserved.")
    print("[NOTE] Use references or instructions to load if needed.")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate OpenCode harness assets from .kilo/ source.",
    )
    parser.add_argument(
        "--harness",
        choices=["all", "skills", "agents", "instructions", "memory", "claude"],
        default="all",
        help="Which asset type to generate (default: all).",
    )
    parser.add_argument(
        "--plugin",
        type=str,
        default=None,
        help="Single skill name to generate (for make generate-plugin P=...).",
    )
    parser.add_argument(
        "--include-all",
        action="store_true",
        default=False,
        help="Copy even skills in the skip list (all 42 skills).",
    )
    parser.add_argument(
        "--global-install",
        action="store_true",
        default=False,
        help="Also copy instructions to ~/.agents/instructions/ for OpenCode auto-load.",
    )
    parser.add_argument(
        "--kilo-root",
        type=str,
        default=None,
        help="Override .kilo/ root directory (default: project .kilo/).",
    )
    parser.add_argument(
        "--opencode-root",
        type=str,
        default=None,
        help="Override .opencode/ root directory (default: project .opencode/).",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    kilo_root = Path(args.kilo_root) if args.kilo_root else ROOT_DIR / ".kilo"
    opencode_root = (
        Path(args.opencode_root) if args.opencode_root else ROOT_DIR / ".opencode"
    )

    opencode_root.mkdir(parents=True, exist_ok=True)

    harness = args.harness
    global_install = args.global_install
    if harness == "all":
        ec = generate_skills(kilo_root, opencode_root, include_all=args.include_all, plugin_filter=args.plugin)
        if ec != 0:
            return ec
        generate_agents(kilo_root, opencode_root)
        generate_instructions(kilo_root, opencode_root, global_install=global_install)
        generate_memory(kilo_root, opencode_root)
        # Claude Code engine
        skip_names = set() if args.include_all else load_skip_list(SKIP_FILE)
        _load_claude_engine().generate_all(kilo_root, ROOT_DIR / ".claude", ROOT_DIR, skip_names=skip_names)
    elif harness == "skills":
        return generate_skills(kilo_root, opencode_root, include_all=args.include_all, plugin_filter=args.plugin)
    elif harness == "agents":
        return generate_agents(kilo_root, opencode_root)
    elif harness == "instructions":
        return generate_instructions(kilo_root, opencode_root, global_install=global_install)
    elif harness == "memory":
        return generate_memory(kilo_root, opencode_root)
    elif harness == "claude":
        skip_names = set() if args.include_all else load_skip_list(SKIP_FILE)
        return _load_claude_engine().generate_all(kilo_root, ROOT_DIR / ".claude", ROOT_DIR, skip_names=skip_names)

    return 0


if __name__ == "__main__":
    sys.exit(main())
