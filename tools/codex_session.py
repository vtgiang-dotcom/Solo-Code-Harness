#!/usr/bin/env python3
"""Codex CLI lifecycle adapter for Solo-Code shared state.

Codex CLI has no project lifecycle hooks, so invoke ``start`` and ``end``
around a session (the launcher does this for interactive sessions).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import uuid
from pathlib import Path

if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.shared_state import SharedState

ROOT = Path(__file__).resolve().parent.parent


def _model() -> str:
    return os.environ.get("CODEX_MODEL", "gpt-5.6-terra")


def start(session_id: str) -> int:
    with SharedState() as state:
        recent = state.get_recent_sessions(limit=3)
        print(f"[codex] session {session_id} started (model={_model()})")
        for item in recent:
            print(f"  [{item['engine']}] {item['summary'][:120]}")
    return 0


def end(session_id: str, summary: str) -> int:
    changed = subprocess.run(
        ["git", "diff", "--name-only"], cwd=ROOT, text=True,
        capture_output=True, check=False,
    ).stdout.splitlines()
    with SharedState() as state:
        state.add_session_entry(
            engine="codex", model=_model(), session_id=session_id,
            summary=summary, files_changed=changed,
        )
    print(f"[codex] session {session_id} recorded ({len(changed)} changed files)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "end"))
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--summary", default="Codex session completed")
    args = parser.parse_args()
    session_id = args.session_id or str(uuid.uuid4())
    return start(session_id) if args.action == "start" else end(session_id, args.summary)


if __name__ == "__main__":
    raise SystemExit(main())
