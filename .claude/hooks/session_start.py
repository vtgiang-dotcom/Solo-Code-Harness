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
  - unseen Gemini/Antigravity handoff reports in
    .gemini/antigravity/handoff/outbox/ (see handoff/README.md) — tracked via
    a local-only "seen" marker at .solocode/gemini-handoff-seen.json so each
    report is announced once, not every session
  - a pending PreCompact recovery checkpoint at
    .solocode/context-checkpoint.json (written by pre_compact.py, see its
    docstring) — surfaced once here then deleted, so a fresh session
    resumes orientation (active feature, unverified changes, next step)
    immediately instead of re-deriving it from git state alone
  - whether the Kilo CLI worker engine is available on this
    machine (binary on PATH + a configured provider profile) -- a signal
    that delegating small, well-specified subtasks to it is *worth
    considering* for cost/latency, not an instruction to always use it
    (see AGENTS.md "Delegating a task to Kilo CLI")
  - prints a SessionStart hookSpecificOutput JSON with additionalContext
"""

from __future__ import annotations

import json
import shutil
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
    """Best-effort read of recent session persistence records. Silent on any failure."""
    tools_dir = cwd / "tools"
    if not (tools_dir / "session_persistence.py").exists():
        return []
    if not (cwd / ".solocode" / "sessions.db").exists():
        return []
    added = False
    try:
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))
            added = True
        import session_persistence  # type: ignore[import-not-found]

        sessions = session_persistence.list_sessions(limit)
        return [
            f"[claude] {s['start_time'][:16]} — {s.get('branch', 'unknown')}@{s.get('commit_hash', 'unknown')[:7]}, {s['files_changed']} uncommit"
            if s['end_time'] else
            f"[claude] {s['start_time'][:16]} — [pre-compact checkpoint, trigger={'auto' if s.get('metadata', {}).get('trigger') == 'auto' else 'unknown'}] branch={s.get('branch', 'unknown')}@{s.get('commit_hash', 'unknown')[:7]}, {s['files_changed']} uncommit"
            for s in sessions
        ]
    except Exception:  # noqa: BLE001 — advisory only
        return []
    finally:
        if added:
            with suppress(ValueError):
                sys.path.remove(str(tools_dir))


def _new_gemini_reports(cwd: Path) -> list[str]:
    """Best-effort: find outbox/*-report.md files not yet announced.

    Tracks announced filenames in .solocode/gemini-handoff-seen.json (local-
    only, gitignored) so a report is surfaced once, then stays quiet.
    Silent on any failure — this is advisory, never required.
    """
    outbox = cwd / ".gemini" / "antigravity" / "handoff" / "outbox"
    if not outbox.is_dir():
        return []
    reports = sorted(f.name for f in outbox.glob("*-report.md"))
    if not reports:
        return []

    seen_file = cwd / ".solocode" / "gemini-handoff-seen.json"
    seen: list[str] = []
    if seen_file.is_file():
        with suppress(Exception):
            seen = json.loads(seen_file.read_text(encoding="utf-8"))

    new = [r for r in reports if r not in seen]
    if new:
        with suppress(Exception):
            seen_file.parent.mkdir(parents=True, exist_ok=True)
            seen_file.write_text(
                json.dumps(sorted(set(seen) | set(new))), encoding="utf-8"
            )
    return new


def _pending_checkpoint(cwd: Path) -> dict | None:
    """Best-effort: read + consume a pending PreCompact recovery checkpoint.

    Deletes the file after reading (surfaced once, not every session) so a
    stale checkpoint from a much earlier compaction never lingers forever.
    Silent on any failure — advisory only, never required.
    """
    checkpoint_file = cwd / ".solocode" / "context-checkpoint.json"
    if not checkpoint_file.is_file():
        return None
    data: dict | None = None
    with suppress(Exception):
        data = json.loads(checkpoint_file.read_text(encoding="utf-8"))
    with suppress(OSError):
        checkpoint_file.unlink()
    if not isinstance(data, dict):
        return None
    return data


def _kilo_available() -> bool:
    """Best-effort: is Kilo CLI (DeepSeek worker) usable on this machine?

    Checks:
    1. Binary exists on PATH or in Antigravity IDE extensions
    2. Kilo server is running and responding on http://127.0.0.1:14096

    Silent on any failure -- advisory only, never required.
    """
    # Check binary availability
    if shutil.which("kilo") is None:
        # Check Antigravity IDE extension path (Windows)
        ide_ext = Path.home() / ".antigravity-ide" / "extensions"
        if not ide_ext.is_dir():
            return False
        kilo_bins = list(ide_ext.glob("kilocode.kilo-code-*/bin/kilo.exe"))
        if not kilo_bins:
            return False

    # Check if server is running
    try:
        import urllib.request
        req = urllib.request.Request(
            "http://127.0.0.1:14096/health",
            headers={"User-Agent": "session_start/kilo-check"}
        )
        with urllib.request.urlopen(req, timeout=1) as resp:
            return resp.status == 200
    except Exception:  # noqa: BLE001
        return False


def _gemini_available(cwd: Path) -> bool:
    """Best-effort: can a task be relayed to Gemini via Antigravity here?

    Requires BOTH the handoff protocol in this repo AND the Antigravity IDE
    installed locally -- the inbox alone means nothing if the human has no
    IDE to open, and the IDE alone means this repo was never wired for
    handoff. This delegation is *not* headless: it costs the user a manual
    relay step, so it is announced as an option, not a default.
    Silent on any failure -- advisory only, never required.
    """
    if not (cwd / ".gemini" / "antigravity" / "handoff" / "inbox").is_dir():
        return False
    if shutil.which("antigravity-ide") is not None:
        return True
    # Default Windows install location -- the IDE does not always add its
    # bin/ directory to PATH.
    ide = Path.home() / "AppData" / "Local" / "Programs" / "Antigravity IDE"
    return ide.is_dir()


def _record_session_start(cwd: Path, session_id: str, branch: str, sha: str) -> bool:
    """Record session start via tools/session_persistence.py."""
    tools_dir = cwd / "tools"
    if not (tools_dir / "session_persistence.py").exists():
        return False
    added = False
    try:
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))
            added = True
        import session_persistence  # type: ignore[import-not-found]

        session_persistence.record_session_start(
            session_id=session_id,
            branch=branch,
            commit=sha,
        )
        return True
    except Exception:  # noqa: BLE001 — advisory only
        return False
    finally:
        if added:
            with suppress(ValueError):
                sys.path.remove(str(tools_dir))


def main() -> int:
    # Consume stdin if present (SessionStart payload) — we don't require it.
    payload: dict = {}
    with suppress(Exception):
        raw = sys.stdin.read()
        if raw.strip():
            payload = json.loads(raw)

    session_id = str(payload.get("session_id", "") or "")

    cwd = Path.cwd()
    try:
        git = _git_info()

        # Record session start if we have a session_id
        if session_id:
            _record_session_start(cwd, session_id, git["branch"], git["sha"])

        pm = _detect_package_manager(cwd)
        sessions = _recent_sessions(cwd)
        new_reports = _new_gemini_reports(cwd)
        checkpoint = _pending_checkpoint(cwd)
        kilo_ready = _kilo_available()
        gemini_ready = _gemini_available(cwd)
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
    if new_reports:
        lines.append(
            f"{len(new_reports)} new Gemini/Antigravity handoff report(s) "
            "in .gemini/antigravity/handoff/outbox/ — read them:"
        )
        lines.extend(f"  - .gemini/antigravity/handoff/outbox/{r}" for r in new_reports)
    if checkpoint:
        lines.append("Resuming from a PreCompact checkpoint left last session:")
        if checkpoint.get("active_feature"):
            lines.append(f"  - active_feature: {checkpoint['active_feature']}")
        if checkpoint.get("unverified_changes"):
            lines.append(f"  - unverified_changes: {checkpoint['unverified_changes']}")
        if checkpoint.get("settled_decisions"):
            lines.append(f"  - settled_decisions: {checkpoint['settled_decisions']}")
        if checkpoint.get("next_immediate_step"):
            lines.append(f"  - next_immediate_step: {checkpoint['next_immediate_step']}")
    if kilo_ready:
        lines.append(
            "Kilo CLI (DeepSeek worker) available — consider delegating small, "
            "well-specified subtasks to it for cost/latency (see AGENTS.md "
            "'Delegating a task to Kilo CLI')."
        )
    if gemini_ready:
        lines.append(
            "Gemini/Antigravity available (manual relay via "
            ".gemini/antigravity/handoff/) — propose it for read-heavy work: "
            "wide audits, multi-file surveys, independent review, UI "
            "verification. Costs the user one relay step, so ask first; "
            "verify 100% of what it returns (see AGENTS.md 'Delegating a "
            "task to Gemini/Antigravity')."
        )

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n".join(lines),
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
