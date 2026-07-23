#!/usr/bin/env python3
"""
Solo-Code Harness Generator — Claude Code engine

Reads .kilo/ (source of truth) and regenerates .claude/ (agents, skills,
commands, instructions, memory, CLAUDE.md).

History: this script used to ALSO generate a .opencode/ mirror. OpenCode
was deprecated in v3.7.0 (100% content-parity mirror of .kilo/, zero unique
capability) and physically removed in v4.0.0 — see .harness.lock and
.kilo/memory/MEMORY.md "Decisions" section. .copilot/ is NOT auto-generated;
it is manually kept in parity with .kilo/ and verified by `tools/garden.py`.

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


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    kilo_root = Path(args.kilo_root) if args.kilo_root else ROOT_DIR / ".kilo"
    skip_names = set() if args.include_all else load_skip_list(SKIP_FILE)
    return _load_claude_engine().generate_all(kilo_root, ROOT_DIR / ".claude", ROOT_DIR, skip_names=skip_names)


if __name__ == "__main__":
    sys.exit(main())
