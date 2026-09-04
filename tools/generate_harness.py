#!/usr/bin/env python3
"""
Solo-Code Harness Generator — Claude Code + OpenCode engines

Reads .kilo/ (source of truth) and regenerates .claude/ (agents, skills,
commands, instructions, memory, CLAUDE.md) plus the .opencode/ engine
(agents, commands, skills, instructions, opencode.json) and the .copilot/
and .gemini/antigravity/ instruction mirrors.

History: this script used to ALSO generate a .opencode/ mirror. OpenCode
was deprecated in v3.7.0 (100% content-parity mirror of .kilo/, zero unique
capability) and physically removed in v4.0.0. It is reintroduced (2026-08)
as a first-class primary engine alongside Claude Code: OpenCode v1.18+ has a
stable native format that Kilo's frontmatter already follows, so the
transform (tools/opencode_engine.py) is near-identity.

.copilot/ and .gemini/ instruction/ files used to be "manually kept in
parity with .kilo/ and verified by tools/garden.py". That left garden
printing "Run 'python tools/generate_harness.py --harness all' to fix"
for a drift this script could not actually fix — the only real remedy was
a hand copy. Instructions are a byte-for-byte copy with no per-engine
transform (see garden.check_instruction_content), so they are now synced
here and that advice is true.

Usage:
    python tools/generate_harness.py --harness claude
    python tools/generate_harness.py --harness opencode
    python tools/generate_harness.py --harness all
    python tools/generate_harness.py --harness all --include-all
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
ROOT_DIR = TOOLS_DIR.parent
SKIP_FILE = TOOLS_DIR / "opencode-skip-skills.txt"  # legacy name, still the skill skip-list
KILO_DIR = ROOT_DIR / ".kilo"
CLAUDE_DIR = ROOT_DIR / ".claude"


def _load_claude_engine():
    """Import the sibling claude_engine module (tools/ may not be on sys.path)."""
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    import claude_engine
    return claude_engine


def _load_opencode_engine():
    """Import the sibling opencode_engine module (tools/ may not be on sys.path)."""
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    import opencode_engine
    return opencode_engine


def load_skip_list(skip_file: Path) -> set[str]:
    """Read skill names to skip (one per line). Returns empty set on error."""
    if not skip_file.is_file():
        print(f"[WARN] Skip file not found: {skip_file}")
        print("[WARN]  -> All skills will be copied.")
        return set()
    names = {line.strip() for line in skip_file.read_text(encoding="utf-8").splitlines() if line.strip()}
    print(f"[INFO] Loaded {len(names)} skip entries from {skip_file.name}")
    for n in sorted(names):
        print(f"       - {n}")
    return names


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate the Claude Code + OpenCode harness engines from .kilo/ source.",
    )
    parser.add_argument(
        "--harness",
        choices=["all", "claude", "opencode"],
        default="all",
        help="Which engine to generate. 'all' emits claude + opencode + the "
             ".copilot/.gemini instruction mirrors.",
    )
    parser.add_argument(
        "--include-all",
        action="store_true",
        default=False,
        help="Copy even skills in the skip list.",
    )
    parser.add_argument(
        "--kilo-root",
        type=str,
        default=None,
        help="Override .kilo/ root directory (default: project .kilo/).",
    )
    return parser


def _sync_mirror_dir(src_dir: Path, mirrors: list[Path], root: Path) -> int:
    """Copy src_dir/*.md into each mirror, updating only files it already has.

    Engines legitimately carry different subsets, and garden only diffs names
    present in both trees, so creating new files here would invent parity
    nobody asked for.
    """
    if not src_dir.is_dir():
        return 0
    synced = 0
    for dst_dir in mirrors:
        if not dst_dir.is_dir():
            continue
        label = dst_dir.relative_to(root).as_posix()
        for src in sorted(src_dir.glob("*.md")):
            dst = dst_dir / src.name
            if not dst.is_file():
                continue  # mirror does not carry this file — leave it
            src_text = src.read_text(encoding="utf-8")
            if dst.read_text(encoding="utf-8") == src_text:
                continue
            dst.write_text(src_text, encoding="utf-8")
            print(f"  [SYNC] {label}/{src.name}")
            synced += 1
    return synced


def sync_instruction_mirrors(kilo_root: Path, root: Path) -> int:
    """Copy .kilo/instruction/*.md to the .copilot/ and .gemini/ mirrors."""
    synced = _sync_mirror_dir(
        kilo_root / "instruction",
        [
            root / ".copilot" / "instruction",
            root / ".gemini" / "antigravity" / "instruction",
        ],
        root,
    )
    print(f"Instruction mirrors synced: {synced}")
    return synced


def sync_memory_mirrors(kilo_root: Path, root: Path) -> int:
    """Copy .kilo/memory/*.md to the .copilot/ mirror.

    .claude/memory/ is handled by claude_engine.generate_all(); .copilot/
    was left to be "manually kept" (see garden.check_memory's docstring),
    which is the same gap that made garden's remediation advice a no-op for
    instructions. Memory files are byte-for-byte copies with no per-engine
    transform, so garden diffs them exactly and this is mechanical.
    """
    synced = _sync_mirror_dir(
        kilo_root / "memory", [root / ".copilot" / "memory"], root
    )
    print(f"Memory mirrors synced: {synced}")
    return synced


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    kilo_root = Path(args.kilo_root) if args.kilo_root else ROOT_DIR / ".kilo"
    skip_names = set() if args.include_all else load_skip_list(SKIP_FILE)

    rc = 0
    if args.harness in ("all", "claude"):
        rc = _load_claude_engine().generate_all(
            kilo_root, ROOT_DIR / ".claude", ROOT_DIR, skip_names=skip_names
        )
    if args.harness in ("all", "opencode"):
        print("\n--- OpenCode engine ---")
        oc_rc = _load_opencode_engine().generate_all(
            kilo_root, ROOT_DIR / ".opencode", ROOT_DIR, skip_names=skip_names
        )
        rc = rc or oc_rc
    if args.harness != "all":
        return rc

    print("\n--- Instruction mirrors (.copilot, .gemini) ---")
    sync_instruction_mirrors(kilo_root, ROOT_DIR)
    print("\n--- Memory mirrors (.copilot) ---")
    sync_memory_mirrors(kilo_root, ROOT_DIR)
    return rc


if __name__ == "__main__":
    sys.exit(main())
