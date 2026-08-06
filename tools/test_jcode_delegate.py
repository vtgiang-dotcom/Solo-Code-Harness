#!/usr/bin/env python3
"""
Tests for tools/jcode_delegate.py — the single-model jcode delegation wrapper.

Covers the parts that don't require the jcode binary to be installed
(command building, guardrail injection, usage logging) with the real
subprocess call mocked out. Dev-only harness self-test — not deployed to
target projects (see tools/deploy.py EXCLUDE_FILES).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import jcode_delegate as jd  # noqa: E402

# ─── model selection ────────────────────────────────────────────────────────

def test_only_pro_model_is_used():
    # The flash/simple tier was removed 2026-07-25 (unreliable in practice);
    # guard against it silently reappearing.
    assert jd.MODEL == "deepseek/deepseek-v4-pro"
    assert "flash" not in jd.MODEL


def test_no_tier_routing_api_remains():
    for removed in ("MODELS", "classify_tier", "CODE_TIER_GUARDRAIL"):
        assert not hasattr(jd, removed), f"{removed} should be gone"


# ─── build_command ──────────────────────────────────────────────────────────

def test_build_command_always_uses_pro_model():
    cmd = jd.build_command("do X", with_tools=False, json_out=True)
    assert jd.MODEL in cmd
    assert "--tool-profile" in cmd and "none" in cmd
    assert "--no-selfdev" in cmd
    assert "--json" in cmd


def test_build_command_routes_allowlisted_model_to_freemodel():
    cmd = jd.build_command(
        "review X", model="gpt-5.6-sol", with_tools=False, json_out=True
    )
    assert "freemodel-openai" in cmd
    assert "gpt-5.6-sol" in cmd
    assert "commandcode" not in cmd


def test_freemodel_allowlist_contains_routing_models():
    assert {"gpt-5.6-sol", "gpt-5.6-terra"} == jd.FREE_MODEL_MODELS


def test_build_command_always_prepends_guardrail():
    # Even a trivial/mechanical prompt gets the guardrail now -- there is no
    # unguarded path left.
    for prompt in ("do Y", "Format this JSON file consistently."):
        cmd = jd.build_command(prompt, with_tools=False, json_out=True)
        prompt_arg = cmd[2]
        assert prompt_arg.startswith("STRICT OPERATING CONSTRAINTS")
        assert prompt_arg.endswith(prompt)


def test_build_command_with_tools_skips_tool_profile_flags():
    cmd = jd.build_command("do Z", with_tools=True, json_out=False)
    assert "--tool-profile" not in cmd
    assert "--no-selfdev" not in cmd
    assert "--json" not in cmd


# ─── main() with subprocess mocked ──────────────────────────────────────────

class _FakeCompletedProcess:
    def __init__(self, returncode: int, stdout: str, stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_main_missing_binary_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(jd.shutil, "which", lambda _name: None)
    rc = jd.main(["some prompt"])
    assert rc == 1
    assert "not found on PATH" in capsys.readouterr().err


def test_main_success_logs_usage(monkeypatch, tmp_path):
    monkeypatch.setattr(jd.shutil, "which", lambda _name: "/usr/bin/jcode")
    fake_log = tmp_path / "jcode-usage.jsonl"
    monkeypatch.setattr(jd, "USAGE_LOG", fake_log)

    fake_result = json.dumps({"text": "ok", "usage": {"input_tokens": 10}})
    with patch.object(
        jd.subprocess, "run",
        return_value=_FakeCompletedProcess(0, fake_result),
    ) as mock_run:
        rc = jd.main(["Format this JSON file."])

    assert rc == 0
    assert mock_run.called
    assert fake_log.is_file()
    logged = json.loads(fake_log.read_text(encoding="utf-8").splitlines()[0])
    assert logged["model"] == jd.MODEL
    assert "tier" not in logged
    assert logged["usage"] == {"input_tokens": 10}


def test_main_accepts_but_ignores_deprecated_tier_flag(monkeypatch, tmp_path, capsys):
    # Old callers passing --tier simple must not break, and must NOT get the
    # removed cheap model.
    monkeypatch.setattr(jd.shutil, "which", lambda _name: "/usr/bin/jcode")
    monkeypatch.setattr(jd, "USAGE_LOG", tmp_path / "usage.jsonl")
    with patch.object(
        jd.subprocess, "run",
        return_value=_FakeCompletedProcess(0, json.dumps({"text": "ok"})),
    ) as mock_run:
        rc = jd.main(["do something", "--tier", "simple"])

    assert rc == 0
    assert jd.MODEL in mock_run.call_args[0][0]
    assert "deprecated" in capsys.readouterr().err.lower()


def test_main_nonzero_exit_propagates(monkeypatch, tmp_path):
    monkeypatch.setattr(jd.shutil, "which", lambda _name: "/usr/bin/jcode")
    monkeypatch.setattr(jd, "USAGE_LOG", tmp_path / "usage.jsonl")
    with patch.object(
        jd.subprocess, "run",
        return_value=_FakeCompletedProcess(2, "", "boom"),
    ):
        rc = jd.main(["do something"])
    assert rc == 2
