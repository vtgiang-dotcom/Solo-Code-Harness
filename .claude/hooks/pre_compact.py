#!/usr/bin/env python3
"""
pre_compact (Claude Code hook) — PreCompact continuity checkpoint.

Fires right before Claude Code compacts (summarizes + clears) the
conversation context -- either automatically (context nearing its limit) or
manually (`/compact`). This is the exact moment session detail is most at
risk of being lost across a compaction boundary.

This hook does NOT try to write the "Decisions" prose itself (a hook is a
deterministic script, not the model) -- it does three things reliably:

  1. Writes an objective, factual checkpoint to `.solocode/shared-state.db`
     (git branch/sha/dirty count, trigger type, timestamp) so there is a
     durable anchor for this point in the session regardless of how good
     the model's own compaction summary turns out to be.
  2. Emits an `additionalContext` reminder telling Claude Code to append any
     settled decision from this session to `.kilo/memory/MEMORY.md` (the
     project's actual cross-session memory) *before* continuing, if it
     hasn't already -- so durable decisions survive compaction instead of
     living only in the about-to-be-summarized transcript.
  3. Asks Claude to also write a small structured checkpoint --
     `.solocode/context-checkpoint.json` (local-only, gitignored, ephemeral --
     same tier as shared-state.db, NOT a MEMORY.md replacement) -- with
     `active_feature`, `unverified_changes`, `settled_decisions`, and
     `next_immediate_step`. `session_start.py` surfaces this once at the
     start of the *next* session (then deletes it) so a fresh session can
     resume orientation immediately instead of re-deriving it from git
     state alone. This is deliberately a next-session recovery aid, not a
     mid-compaction context-survival mechanism -- a hook cannot guarantee
     its own `additionalContext` output survives the model's own summary,
     so the reliable handoff point is the next SessionStart, which this
     harness fully controls.

Wired via .claude/settings.json:
    "PreCompact": [ { "hooks": [ { "type": "command",
        "command": "python .claude/hooks/pre_compact.py" } ] } ]

Behavior (all best-effort, never blocks -- always exits 0):
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


def _log_checkpoint(cwd: Path, session_id: str, model: str, trigger: str,
                     git: dict[str, str | int]) -> bool:
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
            f"[pre-compact checkpoint, trigger={trigger or 'unknown'}] "
            f"branch={git['branch']}@{git['sha']}, {git['dirty']} uncommitted file(s)"
        )
        with shared_state.SharedState() as state:
            state.add_session_entry(
                engine="claude",
                model=model or "claude-code",
                summary=summary,
                session_id=session_id,
            )
        return True
    except Exception:  # noqa: BLE001 -- advisory only
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

    session_id = str(payload.get("session_id", "") or "")
    trigger = str(payload.get("trigger", "") or "")
    model = str(payload.get("model", "") or "")

    cwd = Path.cwd()
    try:
        git = _git_info()
        logged = _log_checkpoint(cwd, session_id, model, trigger, git)
    except Exception:  # noqa: BLE001 -- never block compaction
        return 0

    reminder = (
        "Context is about to be compacted"
        + (f" ({trigger})" if trigger else "")
        + ". Before continuing, do two things:\n"
        "1) If any architectural/scope decision settled this session isn't "
        "yet in .kilo/memory/MEMORY.md's 'Decisions' section, append it now "
        "(source of truth; regenerate .claude/ + sync .copilot/.gemini/ "
        "after) -- durable, cross-session.\n"
        "2) Write a next-session recovery checkpoint to "
        ".solocode/context-checkpoint.json (create/overwrite; local-only, "
        "gitignored, ephemeral) as JSON with exactly these keys: "
        '{"active_feature": "<what you\'re working on, or null>", '
        '"unverified_changes": ["<file paths edited but not yet verified/'
        'tested>"], "settled_decisions": ["<short bullets of decisions made '
        'this session, even ones already in MEMORY.md>"], '
        '"next_immediate_step": "<the single next action to take>"}. '
        "Keep it brief (this is a recovery cue, not a transcript). "
        "A durable git-state checkpoint was "
        + ("logged" if logged else "attempted (shared-state unavailable)")
        + " to .solocode/shared-state.db."
    )

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreCompact",
            "additionalContext": reminder,
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
