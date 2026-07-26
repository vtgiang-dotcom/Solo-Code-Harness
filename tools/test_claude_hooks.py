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


def test_session_start_announces_new_gemini_report(tmp_path, monkeypatch):
    """A new outbox/*-report.md should be announced once, then go quiet."""
    outbox = ROOT / ".gemini" / "antigravity" / "handoff" / "outbox"
    seen_file = ROOT / ".solocode" / "gemini-handoff-seen.json"
    marker = outbox / "pytest-fixture-report.md"
    seen_backup = seen_file.read_text(encoding="utf-8") if seen_file.is_file() else None
    try:
        marker.write_text("---\nslug: pytest-fixture\n---\ntest\n", encoding="utf-8")
        if seen_file.is_file():
            seen_file.unlink()

        r1 = _run("session_start.py", {})
        assert r1.returncode == 0
        assert "pytest-fixture-report.md" in r1.stdout

        r2 = _run("session_start.py", {})
        assert r2.returncode == 0
        assert "pytest-fixture-report.md" not in r2.stdout
    finally:
        marker.unlink(missing_ok=True)
        if seen_backup is not None:
            seen_file.write_text(seen_backup, encoding="utf-8")
        elif seen_file.is_file():
            seen_file.unlink()


def test_session_start_surfaces_and_consumes_checkpoint():
    """A pending .solocode/context-checkpoint.json is surfaced once, then
    deleted so it never leaks into a later, unrelated session."""
    checkpoint_file = ROOT / ".solocode" / "context-checkpoint.json"
    backup = checkpoint_file.read_text(encoding="utf-8") if checkpoint_file.is_file() else None
    try:
        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_file.write_text(json.dumps({
            "active_feature": "pytest-fixture-feature",
            "unverified_changes": ["tools/example.py"],
            "settled_decisions": ["use pytest fixture"],
            "next_immediate_step": "run tests",
        }), encoding="utf-8")

        r1 = _run("session_start.py", {})
        assert r1.returncode == 0
        assert "pytest-fixture-feature" in r1.stdout
        assert not checkpoint_file.exists(), "checkpoint must be consumed (deleted) after read"

        r2 = _run("session_start.py", {})
        assert r2.returncode == 0
        assert "pytest-fixture-feature" not in r2.stdout
    finally:
        if backup is not None:
            checkpoint_file.write_text(backup, encoding="utf-8")
        elif checkpoint_file.is_file():
            checkpoint_file.unlink()


def test_session_start_no_checkpoint_is_silent():
    checkpoint_file = ROOT / ".solocode" / "context-checkpoint.json"
    assert not checkpoint_file.exists()  # sanity: previous test cleaned up
    r = _run("session_start.py", {})
    assert r.returncode == 0
    assert "Resuming from a PreCompact checkpoint" not in r.stdout


def test_session_start_malformed_checkpoint_is_silent():
    """A corrupt/malformed checkpoint file must never crash SessionStart —
    advisory only. It's still consumed (deleted) so it doesn't linger."""
    checkpoint_file = ROOT / ".solocode" / "context-checkpoint.json"
    backup = checkpoint_file.read_text(encoding="utf-8") if checkpoint_file.is_file() else None
    try:
        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_file.write_text("not-json{{{", encoding="utf-8")
        r = _run("session_start.py", {})
        assert r.returncode == 0
        assert "Resuming from a PreCompact checkpoint" not in r.stdout
    finally:
        if backup is not None:
            checkpoint_file.write_text(backup, encoding="utf-8")
        elif checkpoint_file.is_file():
            checkpoint_file.unlink()


def test_session_start_jcode_detection_never_crashes():
    """_jcode_available() is best-effort: whatever the real result on this
    machine, SessionStart must never crash and must exit 0 either way."""
    r = _run("session_start.py", {})
    assert r.returncode == 0
    out = json.loads(r.stdout)
    ctx = out["hookSpecificOutput"]["additionalContext"]
    # Whichever branch fired, the mention (if any) must reference AGENTS.md,
    # never silently claim availability without pointing to the how-to.
    if "jcode" in ctx:
        assert "AGENTS.md" in ctx


def test_jcode_available_false_when_binary_missing(monkeypatch):
    """No jcode on PATH -> must report unavailable, never crash."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "session_start_module", HOOKS / "session_start.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    assert mod._jcode_available() is False


def test_jcode_available_false_when_config_missing(monkeypatch, tmp_path):
    """jcode binary present but ~/.jcode/config.toml missing -> unavailable."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "session_start_module", HOOKS / "session_start.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    monkeypatch.setattr(mod.shutil, "which", lambda name: "/usr/bin/jcode")
    monkeypatch.setattr(mod.Path, "home", lambda: tmp_path)
    assert mod._jcode_available() is False


def test_jcode_available_true_when_configured(monkeypatch, tmp_path):
    """jcode binary present + config.toml has default_provider -> available."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "session_start_module", HOOKS / "session_start.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    jcode_dir = tmp_path / ".jcode"
    jcode_dir.mkdir()
    (jcode_dir / "config.toml").write_text(
        '[provider]\ndefault_provider = "commandcode"\n', encoding="utf-8"
    )
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/usr/bin/jcode")
    monkeypatch.setattr(mod.Path, "home", lambda: tmp_path)
    assert mod._jcode_available() is True


def _load_session_start():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "session_start_module", HOOKS / "session_start.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_gemini_available_false_without_handoff_dir(monkeypatch, tmp_path):
    """No handoff/inbox/ in the repo -> this project was never wired for
    Gemini relay, so it must not be announced even if the IDE is installed."""
    mod = _load_session_start()
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/usr/bin/antigravity-ide")
    assert mod._gemini_available(tmp_path) is False


def test_gemini_available_false_without_ide(monkeypatch, tmp_path):
    """Handoff dir present but no Antigravity IDE anywhere -> unavailable.

    The relay needs a human with the IDE open; announcing it on a machine
    without the IDE would send the user on an errand they cannot run.
    """
    mod = _load_session_start()
    (tmp_path / ".gemini" / "antigravity" / "handoff" / "inbox").mkdir(parents=True)
    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    monkeypatch.setattr(mod.Path, "home", lambda: tmp_path)
    assert mod._gemini_available(tmp_path) is False


def test_gemini_available_true_with_handoff_and_ide(monkeypatch, tmp_path):
    """Handoff dir + IDE on PATH -> available."""
    mod = _load_session_start()
    (tmp_path / ".gemini" / "antigravity" / "handoff" / "inbox").mkdir(parents=True)
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/usr/bin/antigravity-ide")
    assert mod._gemini_available(tmp_path) is True


def test_gemini_available_true_via_default_install_dir(monkeypatch, tmp_path):
    """IDE not on PATH but present at the default Windows location.

    The Antigravity installer does not reliably add its bin/ to PATH, so
    PATH-only detection would report unavailable on a working machine.
    """
    mod = _load_session_start()
    (tmp_path / ".gemini" / "antigravity" / "handoff" / "inbox").mkdir(parents=True)
    (tmp_path / "AppData" / "Local" / "Programs" / "Antigravity IDE").mkdir(parents=True)
    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    monkeypatch.setattr(mod.Path, "home", lambda: tmp_path)
    assert mod._gemini_available(tmp_path) is True


def test_session_start_gemini_mention_points_to_agents_md():
    """Like jcode, an availability claim must carry a pointer to the how-to,
    never advertise a capability the reader cannot look up."""
    r = _run("session_start.py", {})
    assert r.returncode == 0
    ctx = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
    if "Gemini/Antigravity available" in ctx:
        assert "AGENTS.md" in ctx


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


# ─── pre_compact.py ─────────────────────────────────────────────────────────

def test_pre_compact_exists():
    assert (HOOKS / "pre_compact.py").exists()


def test_pre_compact_emits_context_json():
    r = _run("pre_compact.py", {"session_id": "t1", "trigger": "auto", "model": "claude"})
    assert r.returncode == 0
    out = json.loads(r.stdout)
    hso = out["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreCompact"
    assert "MEMORY.md" in hso["additionalContext"]


def test_pre_compact_requests_context_checkpoint_schema():
    """The reminder must ask for the exact checkpoint schema session_start.py
    knows how to read: active_feature, unverified_changes,
    settled_decisions, next_immediate_step."""
    r = _run("pre_compact.py", {"session_id": "t1", "trigger": "auto", "model": "claude"})
    ctx = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
    assert ".solocode/context-checkpoint.json" in ctx
    for key in ("active_feature", "unverified_changes", "settled_decisions", "next_immediate_step"):
        assert key in ctx, f"checkpoint schema key {key!r} missing from reminder"


def test_pre_compact_empty_stdin_exits_zero():
    r = _run("pre_compact.py", "")
    assert r.returncode == 0


def test_pre_compact_malformed_stdin_exits_zero():
    r = _run("pre_compact.py", "not-json")
    assert r.returncode == 0


# ─── settings.json wiring ───────────────────────────────────────────────────

# ─── memory_gate.py ─────────────────────────────────────────────────────────

def test_memory_gate_exists():
    assert (HOOKS / "memory_gate.py").exists()


def test_memory_gate_ignores_non_write_tools():
    r = _run("memory_gate.py", {"tool_name": "Read"})
    assert r.returncode == 0
    assert r.stderr == ""


def test_memory_gate_empty_stdin_exits_zero():
    r = _run("memory_gate.py", "")
    assert r.returncode == 0


def test_memory_gate_malformed_stdin_exits_zero():
    r = _run("memory_gate.py", "not-json")
    assert r.returncode == 0


def test_memory_gate_current_memory_under_hard_limit():
    """Regression guard: .claude/memory/MEMORY.md must stay under the hard
    cap (8,000 chars) so this hook never blocks a routine session."""
    r = _run("memory_gate.py", {"tool_name": "Edit",
                                 "tool_input": {"file_path": ".claude/memory/MEMORY.md"}})
    assert r.returncode == 0, r.stderr


def test_memory_gate_never_caps_decisions_archive(tmp_path, monkeypatch):
    """decisions-archive.md is cold storage (not auto-loaded into session
    context) and must be exempt from the size cap by design -- an entry
    moved out of MEMORY.md must never get stuck unable to land here."""
    mem_dir = tmp_path / ".claude" / "memory"
    mem_dir.mkdir(parents=True)
    (mem_dir / "decisions-archive.md").write_text("x" * 50000, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    r = subprocess.run(
        [sys.executable, str(HOOKS / "memory_gate.py")],
        input=json.dumps({"tool_name": "Write",
                          "tool_input": {"file_path": ".claude/memory/decisions-archive.md"}}),
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0, r.stderr


def test_memory_gate_blocks_oversized_file(tmp_path, monkeypatch):
    mem_dir = tmp_path / ".claude" / "memory"
    mem_dir.mkdir(parents=True)
    (mem_dir / "MEMORY.md").write_text("x" * 8500, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    r = subprocess.run(
        [sys.executable, str(HOOKS / "memory_gate.py")],
        input=json.dumps({"tool_name": "Write",
                          "tool_input": {"file_path": ".claude/memory/MEMORY.md"}}),
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 2
    assert "BLOCKED" in r.stderr


def test_memory_gate_warns_but_passes_between_thresholds(tmp_path, monkeypatch):
    mem_dir = tmp_path / ".claude" / "memory"
    mem_dir.mkdir(parents=True)
    (mem_dir / "MEMORY.md").write_text("x" * 5000, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    r = subprocess.run(
        [sys.executable, str(HOOKS / "memory_gate.py")],
        input=json.dumps({"tool_name": "Edit",
                          "tool_input": {"file_path": ".claude/memory/MEMORY.md"}}),
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0
    assert "WARN" in r.stderr


# ─── settings.json wiring ───────────────────────────────────────────────────

def test_settings_registers_all_lifecycle_hooks():
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    hooks = settings["hooks"]
    commands = json.dumps(hooks)
    assert "PreToolUse" in hooks
    assert "PostToolUse" in hooks
    assert "PreCompact" in hooks
    assert "SessionStart" in hooks
    assert "SessionEnd" in hooks
    for hook_file in ("guard.py", "quality_gate.py", "security_post.py",
                      "pre_compact.py", "session_start.py", "session_end.py",
                      "memory_gate.py"):
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
