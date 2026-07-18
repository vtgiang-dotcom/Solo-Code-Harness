#!/usr/bin/env python3
"""
session_start (Claude Code hook) — SessionStart context loader.

Python port of the SessionStart concept from .kilo/hooks/session/session-start.js.
Stdlib-only. Emits project context to Claude via `additionalContext` so a fresh
session immediately knows git state, package manager, and recent cross-engine work.

Wired via .claude/settings.json:
    "SessionStart": [ { "hooks": [ { "type": "command",
        "command": "python .claude/hooks/session_start.py" } ] } ]

Behavior (all best-effort, never blocks — always exits 0):
  - git branch / short SHA / dirty-file count
  - detected package manager (pnpm/yarn/bun/npm)
  - up to 3 most recent shared-state sessions (any engine) if the local
    SQLite state + tools/shared_state.py are available
  - prints a SessionStart hookSpecificOutput JSON with additionalContext
"""

from __future__ import annotations

import json
import subprocess
import sys
from contextlib import suppress
from pathlib import Path


def _git(args: list[str]) -> str:
    try:
        res = subprocess.run(
            ["git", *args], capture_output=True, text=True, timeout=5
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return ""


def _git_info() -> dict[str, str | int]:
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"
    sha = _git(["rev-parse", "--short", "HEAD"]) or "unknown"
    status = _git(["status", "--porcelain"])
    dirty = len([ln for ln in status.split("\n") if ln.strip()]) if status else 0
    return {"branch": branch, "sha": sha, "dirty": dirty}


def _detect_package_manager(cwd: Path) -> str:
    for lockfile, name in (
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"),
        ("bun.lockb", "bun"),
        ("package-lock.json", "npm"),
    ):
        if (cwd / lockfile).exists():
            return name
    return ""


def _recent_sessions(cwd: Path, limit: int = 3) -> list[str]:
    """Best-effort read of recent shared-state sessions. Silent on any failure."""
    tools_dir = cwd / "tools"
    if not (tools_dir / "shared_state.py").exists():
        return []
    if not (cwd / ".solocode" / "shared-state.db").exists():
        return []
    added = False
    try:
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))
            added = True
        import shared_state  # type: ignore[import-not-found]

        with shared_state.SharedState() as state:
            rows = state.get_recent_sessions(limit)
        return [
            f"[{r['engine']}] {str(r['timestamp'])[:16]} — {str(r['summary'])[:70]}"
            for r in rows
        ]
    except Exception:  # noqa: BLE001 — advisory only
        return []
    finally:
        if added:
            with suppress(ValueError):
                sys.path.remove(str(tools_dir))


def main() -> int:
    # Consume stdin if present (SessionStart payload) — we don't require it.
    with suppress(Exception):
        sys.stdin.read()

    cwd = Path.cwd()
    try:
        git = _git_info()
        pm = _detect_package_manager(cwd)
        sessions = _recent_sessions(cwd)
    except Exception:  # noqa: BLE001 — never crash session startup
        return 0

    lines = [
        f"Git: branch {git['branch']} ({git['sha']}), {git['dirty']} uncommitted file(s).",
    ]
    if pm:
        lines.append(f"Package manager: {pm}.")
    if sessions:
        lines.append("Recent cross-engine sessions:")
        lines.extend(f"  - {s}" for s in sessions)

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n".join(lines),
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
