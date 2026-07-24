#!/usr/bin/env python3
"""
Tests for tools/jcode_delegate.py — the two-tier jcode delegation wrapper.

Covers the parts that don't require the jcode binary to be installed
(classification heuristic, command building, usage logging) with the real
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

# ─── classify_tier ──────────────────────────────────────────────────────────

def test_classify_simple_default():
    assert jd.classify_tier("Format this JSON file consistently.") == "simple"


def test_classify_code_on_refactor_keyword():
    assert jd.classify_tier("Refactor this function to remove duplication.") == "code"


def test_classify_code_on_bug_keyword():
    assert jd.classify_tier("There is a bug causing a race condition here.") == "code"


def test_classify_biased_toward_cheap_tier():
    # Ambiguous/neutral prompt with no code-tier hints -> stays cheap.
    assert jd.classify_tier("Write a short summary of this changelog entry.") == "simple"


# ─── build_command ──────────────────────────────────────────────────────────

def test_build_command_simple_tier_no_guardrail():
    cmd = jd.build_command("do X", "simple", with_tools=False, json_out=True)
    assert jd.MODELS["simple"] in cmd
    assert "do X" in cmd
    assert "--tool-profile" in cmd and "none" in cmd
    assert "--no-selfdev" in cmd
    assert "--json" in cmd


def test_build_command_code_tier_prepends_guardrail():
    cmd = jd.build_command("do Y", "code", with_tools=False, json_out=True)
    assert jd.MODELS["code"] in cmd
    prompt_arg = cmd[2]
    assert prompt_arg.startswith("STRICT OPERATING CONSTRAINTS")
    assert prompt_arg.endswith("do Y")


def test_build_command_with_tools_skips_tool_profile_flags():
    cmd = jd.build_command("do Z", "simple", with_tools=True, json_out=False)
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
        rc = jd.main(["Format this JSON file.", "--tier", "simple"])

    assert rc == 0
    assert mock_run.called
    assert fake_log.is_file()
    logged = json.loads(fake_log.read_text(encoding="utf-8").splitlines()[0])
    assert logged["tier"] == "simple"
    assert logged["model"] == jd.MODELS["simple"]
    assert logged["usage"] == {"input_tokens": 10}


def test_main_nonzero_exit_propagates(monkeypatch, tmp_path):
    monkeypatch.setattr(jd.shutil, "which", lambda _name: "/usr/bin/jcode")
    monkeypatch.setattr(jd, "USAGE_LOG", tmp_path / "usage.jsonl")
    with patch.object(
        jd.subprocess, "run",
        return_value=_FakeCompletedProcess(2, "", "boom"),
    ):
        rc = jd.main(["do something", "--tier", "code"])
    assert rc == 2
