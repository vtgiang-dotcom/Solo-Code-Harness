#!/usr/bin/env python3
"""
session_end (Claude Code hook) — SessionEnd shared-state logger.

Python port of the SessionEnd concept from .kilo/hooks/session/session-end.js.
Stdlib-only. Persists a compact session summary into the LOCAL shared-state
SQLite (.solocode/shared-state.db) with engine="claude", so other engines see
what Claude Code did on this machine. Also prints a short summary to stderr.

Wired via .claude/settings.json:
    "SessionEnd": [ { "hooks": [ { "type": "command",
        "command": "python .claude/hooks/session_end.py" } ] } ]

Behavior (all best-effort, never blocks — always exits 0):
  - counts staged/unstaged changes via git
  - writes one session_log row via tools/shared_state.py (if available)
  - the DB is local-only + gitignored + deploy-excluded — never committed
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


def _changed_files() -> tuple[int, int, list[str]]:
    unstaged = _git(["diff", "--name-only"])
    staged = _git(["diff", "--cached", "--name-only"])
    u = [f for f in unstaged.split("\n") if f.strip()] if unstaged else []
    s = [f for f in staged.split("\n") if f.strip()] if staged else []
    return len(s), len(u), sorted(set(s) | set(u))


def _log_to_shared_state(cwd: Path, model: str, session_id: str,
                         files: list[str]) -> bool:
    tools_dir = cwd / "tools"
    if not (tools_dir / "shared_state.py").exists():
        return False
    added = False
    try:
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))
            added = True
        import shared_state  # type: ignore[import-not-found]

        summary = (
            f"Claude Code session: {len(files)} file(s) touched"
            if files else "Claude Code session (no file changes)"
        )
        with shared_state.SharedState() as state:
            state.add_session_entry(
                engine="claude",
                model=model or "claude-code",
                summary=summary,
                session_id=session_id,
                files_changed=files,
            )
        return True
    except Exception:  # noqa: BLE001 — advisory only
        return False
    finally:
        if added:
            with suppress(ValueError):
                sys.path.remove(str(tools_dir))


def main() -> int:
    payload: dict = {}
    raw = ""
    with suppress(Exception):
        raw = sys.stdin.read()
    if raw.strip():
        with suppress(json.JSONDecodeError, ValueError):
            payload = json.loads(raw)

    model = str(payload.get("model", "") or "")
    session_id = str(payload.get("session_id", "") or "")

    cwd = Path.cwd()
    try:
        staged, unstaged, files = _changed_files()
        logged = _log_to_shared_state(cwd, model, session_id, files)
    except Exception:  # noqa: BLE001 — never crash session end
        return 0

    sys.stderr.write(
        "\n[Solo-Code] Session ended — "
        f"{staged} staged + {unstaged} unstaged change(s)"
        + (" | logged to shared-state" if logged else "")
        + ".\n"
    )
    if staged + unstaged > 0:
        sys.stderr.write("[Solo-Code] Remember to commit or stash uncommitted changes.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
