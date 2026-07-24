#!/usr/bin/env python3
"""
memory_gate (Claude Code hook) — PostToolUse memory file size gate.

Python port of .kilo/hooks/post-tool-use/memory-manager.js. Stdlib-only.
Memory files (.claude/memory/*) are loaded into EVERY session's context via
SessionStart/CLAUDE.md references, so unbounded growth silently taxes every
future session's token budget. This hook is the Claude Code counterpart to
Kilo's memory-manager.js (which only ever gated .kilo/memory/ writes made
through the Kilo engine — Claude Code writes to .claude/memory/ went
ungated until this hook existed).

Wired via .claude/settings.json:
    "PostToolUse": [ { "matcher": "Edit|Write|MultiEdit",
        "hooks": [ { "type": "command",
            "command": "python .claude/hooks/memory_gate.py" } ] } ]

Behavior:
  - Reads the PostToolUse JSON from stdin: {tool_name, tool_input:{file_path}}.
  - Only checks on Write/Edit/MultiEdit (matches memory-manager.js semantics).
  - After every such edit, checks char count of .claude/memory/*.md files:
      WARN at 4,000 chars — advisory message to stderr, exit 0.
      HARD at 8,000 chars — block via exit 2 (Claude Code re-prompts the
      model with stderr as feedback), demanding compaction before continuing.
  - Any error (missing dir, unreadable file, malformed stdin) -> silent exit 0.
"""

from __future__ import annotations

import json
import sys
from contextlib import suppress
from pathlib import Path

WARN_CHARS = 4000
HARD_CHARS = 8000
MEMORY_FILES = ("MEMORY.md", "project-conventions.md", "harness-design-intent.md")


def main() -> int:
    raw = ""
    with suppress(Exception):
        raw = sys.stdin.read()

    payload: dict = {}
    if raw.strip():
        with suppress(json.JSONDecodeError, ValueError):
            payload = json.loads(raw)

    if payload.get("tool_name", "") not in ("Write", "Edit", "MultiEdit"):
        return 0

    memory_dir = Path.cwd() / ".claude" / "memory"
    if not memory_dir.is_dir():
        return 0

    warnings: list[tuple[str, int]] = []
    blocks: list[tuple[str, int]] = []

    for name in MEMORY_FILES:
        path = memory_dir / name
        if not path.exists():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        count = len(content)
        if count > HARD_CHARS:
            blocks.append((name, count))
        elif count > WARN_CHARS:
            warnings.append((name, count))

    for name, count in warnings:
        sys.stderr.write(
            f"\n[MemoryGate] WARN {name}: {count:,} chars "
            f"(limit {WARN_CHARS:,}, {HARD_CHARS - count:,} remaining before block).\n"
            "  Suggest: prune stale entries, use brief links, move details to "
            "dedicated files.\n"
        )

    if blocks:
        for name, count in blocks:
            sys.stderr.write(
                f"\n[MemoryGate] BLOCKED {name}: {count:,} chars exceeds hard "
                f"limit {HARD_CHARS:,} by {count - HARD_CHARS:,}.\n"
                "  Memory files load into EVERY session context. "
                "Compact this file before continuing: keep only high-signal,\n"
                "  frequently-referenced items; move verbose history to git "
                "commit messages (already durable) instead of prose here.\n"
            )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
