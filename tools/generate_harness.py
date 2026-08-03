#!/usr/bin/env python3
"""
Solo-Code Harness Generator — Claude Code engine

Reads .kilo/ (source of truth) and regenerates .claude/ (agents, skills,
commands, instructions, memory, CLAUDE.md) plus the .copilot/ and
.gemini/antigravity/ instruction mirrors.

History: this script used to ALSO generate a .opencode/ mirror. OpenCode
was deprecated in v3.7.0 (100% content-parity mirror of .kilo/, zero unique
capability) and physically removed in v4.0.0 — see .harness.lock and
.kilo/memory/MEMORY.md "Decisions" section.

.copilot/ and .gemini/ instruction/ files used to be "manually kept in
parity with .kilo/ and verified by tools/garden.py". That left garden
printing "Run 'python tools/generate_harness.py --harness all' to fix"
for a drift this script could not actually fix — the only real remedy was
a hand copy. Instructions are a byte-for-byte copy with no per-engine
transform (see garden.check_instruction_content), so they are now synced
here and that advice is true.

Usage:
    python tools/generate_harness.py --harness claude
    python tools/generate_harness.py --harness claude --include-all
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
        description="Generate the Claude Code harness engine from .kilo/ source.",
    )
    parser.add_argument(
        "--harness",
        choices=["all", "claude"],
        default="all",
        help="Both values do the same thing now (claude is the only generated "
             "engine) — kept for backward-compatible scripts/CI.",
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


def sync_instruction_mirrors(kilo_root: Path, root: Path) -> int:
    """Copy .kilo/instruction/*.md to the .copilot/ and .gemini/ mirrors.

    Only files the mirror ALREADY has are updated. Engines legitimately carry
    different instruction subsets, so adding new files here would invent
    parity that garden.check_instructions() never asked for — that check
    only flags content drift on names present in both.
    """
    src_dir = kilo_root / "instruction"
    if not src_dir.is_dir():
        return 0

    mirrors = [
        root / ".copilot" / "instruction",
        root / ".gemini" / "antigravity" / "instruction",
    ]
    synced = 0
    for dst_dir in mirrors:
        if not dst_dir.is_dir():
            continue
        label = dst_dir.relative_to(root).as_posix()
        for src in sorted(src_dir.glob("*.md")):
            dst = dst_dir / src.name
            if not dst.is_file():
                continue  # mirror does not carry this instruction — leave it
            src_text = src.read_text(encoding="utf-8")
            if dst.read_text(encoding="utf-8") == src_text:
                continue
            dst.write_text(src_text, encoding="utf-8")
            print(f"  [SYNC] {label}/{src.name}")
            synced += 1
    print(f"Instruction mirrors synced: {synced}")
    return synced


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    kilo_root = Path(args.kilo_root) if args.kilo_root else ROOT_DIR / ".kilo"
    skip_names = set() if args.include_all else load_skip_list(SKIP_FILE)
    rc = _load_claude_engine().generate_all(
        kilo_root, ROOT_DIR / ".claude", ROOT_DIR, skip_names=skip_names
    )
    print("\n--- Instruction mirrors (.copilot, .gemini) ---")
    sync_instruction_mirrors(kilo_root, ROOT_DIR)
    return rc


if __name__ == "__main__":
    sys.exit(main())
