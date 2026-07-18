#!/usr/bin/env python3
"""
Claude Lifecycle Hook Tests
===========================
Runs the PostToolUse (quality_gate, security_post) and SessionStart/SessionEnd
hooks as subprocesses with JSON payloads on stdin. These hooks are advisory and
must ALWAYS exit 0 (never block the tool call / session).

Usage:
    python -m pytest tools/test_claude_hooks.py -v
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude" / "hooks"


def _run(hook: str, payload: dict | str) -> subprocess.CompletedProcess[str]:
    data = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        [sys.executable, str(HOOKS / hook)],
        input=data,
        capture_output=True,
        text=True,
        timeout=30,
    )


# ─── quality_gate.py ────────────────────────────────────────────────────────

def test_quality_gate_exists():
    assert (HOOKS / "quality_gate.py").exists()


def test_quality_gate_nonexistent_file_exits_zero():
    r = _run("quality_gate.py", {"tool_input": {"file_path": "does/not/exist.py"}})
    assert r.returncode == 0


def test_quality_gate_empty_payload_exits_zero():
    r = _run("quality_gate.py", {})
    assert r.returncode == 0


def test_quality_gate_malformed_stdin_exits_zero():
    r = _run("quality_gate.py", "not json at all")
    assert r.returncode == 0


def test_quality_gate_unknown_extension_exits_zero():
    # A real file with an extension we don't format — must be a no-op.
    r = _run("quality_gate.py", {"tool_input": {"file_path": str(ROOT / "README.md")}})
    assert r.returncode == 0


# ─── security_post.py ───────────────────────────────────────────────────────

def test_security_post_exists():
    assert (HOOKS / "security_post.py").exists()


def test_security_post_ignores_non_bash():
    r = _run("security_post.py", {"tool_name": "Edit", "tool_input": {"file_path": "x.py"}})
    assert r.returncode == 0
    assert r.stderr.strip() == ""


def test_security_post_ignores_non_git_bash():
    r = _run("security_post.py", {"tool_name": "Bash", "tool_input": {"command": "ls -la"}})
    assert r.returncode == 0
    assert "SECURITY ALERT" not in r.stderr


def test_security_post_git_commit_exits_zero():
    # Clean tree or not, the hook is non-blocking and must exit 0.
    r = _run("security_post.py", {"tool_name": "Bash", "tool_input": {"command": "git commit -m wip"}})
    assert r.returncode == 0


def test_security_post_malformed_stdin_exits_zero():
    r = _run("security_post.py", "garbage")
    assert r.returncode == 0


# ─── session_start.py ───────────────────────────────────────────────────────

def test_session_start_exists():
    assert (HOOKS / "session_start.py").exists()


def test_session_start_emits_context_json():
    r = _run("session_start.py", {"session_id": "t1", "source": "startup", "model": "claude"})
    assert r.returncode == 0
    out = json.loads(r.stdout)
    hso = out["hookSpecificOutput"]
    assert hso["hookEventName"] == "SessionStart"
    assert "additionalContext" in hso
    assert "Git:" in hso["additionalContext"]


def test_session_start_empty_stdin_exits_zero():
    r = _run("session_start.py", "")
    assert r.returncode == 0


# ─── session_end.py ─────────────────────────────────────────────────────────

def test_session_end_exists():
    assert (HOOKS / "session_end.py").exists()


def test_session_end_exits_zero_and_reports():
    r = _run("session_end.py", {"session_id": "t1", "reason": "other", "model": "claude"})
    assert r.returncode == 0
    assert "Session ended" in r.stderr


def test_session_end_malformed_stdin_exits_zero():
    r = _run("session_end.py", "not-json")
    assert r.returncode == 0


# ─── settings.json wiring ───────────────────────────────────────────────────

def test_settings_registers_all_lifecycle_hooks():
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    hooks = settings["hooks"]
    commands = json.dumps(hooks)
    assert "PreToolUse" in hooks
    assert "PostToolUse" in hooks
    assert "SessionStart" in hooks
    assert "SessionEnd" in hooks
    for hook_file in ("guard.py", "quality_gate.py", "security_post.py",
                      "session_start.py", "session_end.py"):
        assert hook_file in commands, f"{hook_file} not wired in settings.json"


def test_shared_state_accepts_claude_engine():
    """Compatibility guard: session_end logs with engine='claude'."""
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        import shared_state
        assert "claude" in shared_state.VALID_ENGINES
        # Other engines must remain valid (no regression).
        for e in ("kilo", "opencode", "copilot", "gemini"):
            assert e in shared_state.VALID_ENGINES
    finally:
        sys.path.remove(str(ROOT / "tools"))
