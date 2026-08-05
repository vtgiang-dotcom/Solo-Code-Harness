"""Tests for tools/approve_api_key.py.

The failure this script addresses is invisible to every non-interactive check:
Claude Code stores a "no" from its custom-key prompt in ~/.claude.json and then
refuses interactive sessions, while `-p` and `--bare` ignore the list entirely.
So these tests care most about `--check` -- the launcher preflight that is now
the only thing standing between a deployed project and a silent auth failure.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import approve_api_key as approver  # noqa: E402

KEY = "x" * 24
FINGERPRINT = KEY[-20:]


def _config(tmp_path: Path, approved: list[str], rejected: list[str]) -> Path:
    f = tmp_path / ".claude.json"
    f.write_text(
        json.dumps({"customApiKeyResponses": {"approved": approved, "rejected": rejected}}),
        encoding="utf-8",
    )
    return f


# --- key_from_env_file -------------------------------------------------------


def test_key_from_env_file_ignores_comments_and_other_vars(tmp_path):
    f = tmp_path / ".env"
    f.write_text(
        "# ANTHROPIC_API_KEY=decoy\n"
        "ANTHROPIC_MODEL=some-model\n"
        f'ANTHROPIC_API_KEY="{KEY}"\n',
        encoding="utf-8",
    )
    assert approver.key_from_env_file(f) == KEY


@pytest.mark.parametrize("raw", [
    f"ANTHROPIC_API_KEY={KEY}\n",
    f'ANTHROPIC_API_KEY="{KEY}"\n',
    f"ANTHROPIC_API_KEY='{KEY}'\n",
    f"ANTHROPIC_API_KEY = {KEY} \n",
])
def test_key_from_env_file_strips_quotes_and_space(tmp_path, raw):
    f = tmp_path / ".env"
    f.write_text(raw, encoding="utf-8")
    assert approver.key_from_env_file(f) == KEY


def test_key_from_env_file_returns_empty_on_missing_file(tmp_path):
    assert approver.key_from_env_file(tmp_path / "absent") == ""


# --- resolve_key -------------------------------------------------------------


def test_resolve_key_prefers_shell_over_env_file(tmp_path, monkeypatch):
    """The shell key is the one the session will actually use, so a stale key
    left in .env must not be the one reported on."""
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=stale\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    key, source = approver.resolve_key()
    assert key == KEY
    assert source == "shell environment"


def test_resolve_key_falls_back_to_env_file(tmp_path, monkeypatch):
    """The launcher is what loads .env. Standing in a deployed project with a
    plain shell, .env is the only place the key exists."""
    (tmp_path / ".env").write_text(f"ANTHROPIC_API_KEY={KEY}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    key, source = approver.resolve_key()
    assert key == KEY
    assert ".env" in source


# --- is_rejected -------------------------------------------------------------


def test_is_rejected_true_when_fingerprint_listed(tmp_path):
    assert approver.is_rejected(KEY, _config(tmp_path, [], [FINGERPRINT])) is True


def test_is_rejected_false_when_approved(tmp_path):
    assert approver.is_rejected(KEY, _config(tmp_path, [FINGERPRINT], [])) is False


def test_is_rejected_matches_on_last_20_chars_only(tmp_path):
    """Claude Code fingerprints a custom key by its trailing 20 characters, so a
    different-prefix key with the same tail is the same stored decision."""
    other = "zzzz" + KEY[-20:]
    assert approver.is_rejected(other, _config(tmp_path, [], [FINGERPRINT])) is True


@pytest.mark.parametrize("payload", ["", "{not json", "{}", '{"customApiKeyResponses": {}}'])
def test_is_rejected_false_on_unusable_config(tmp_path, payload):
    """Every uncertain case must answer False: this gates a launcher preflight,
    and guessing "rejected" would nag on every start over no evidence."""
    f = tmp_path / ".claude.json"
    f.write_text(payload, encoding="utf-8")
    assert approver.is_rejected(KEY, f) is False


def test_is_rejected_false_on_missing_config(tmp_path):
    assert approver.is_rejected(KEY, tmp_path / "absent.json") is False


def test_is_rejected_false_on_short_key(tmp_path):
    assert approver.is_rejected("short", _config(tmp_path, [], [FINGERPRINT])) is False


# --- check (the launcher preflight) ------------------------------------------


def _run_check(tmp_path, monkeypatch, *, rejected: list[str], key: str = KEY) -> int:
    monkeypatch.setattr(approver, "CONFIG", _config(tmp_path, [], rejected))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", key)
    monkeypatch.setattr(sys, "argv", ["approve_api_key.py", "--check"])
    return approver.main()


def test_check_signals_rejected_key(tmp_path, monkeypatch, capsys):
    """The one behaviour that makes this a preflight rather than a report."""
    assert _run_check(tmp_path, monkeypatch, rejected=[FINGERPRINT]) == approver.EXIT_REJECTED
    out = capsys.readouterr().out
    assert "rejected" in out
    assert "--apply" in out


def test_check_is_silent_when_key_is_fine(tmp_path, monkeypatch, capsys):
    """It runs on every launch, so a healthy key must produce no output at all."""
    assert _run_check(tmp_path, monkeypatch, rejected=[]) == 0
    assert capsys.readouterr().out == ""


def test_check_is_silent_with_no_key_at_all(tmp_path, monkeypatch, capsys):
    """A missing key is the launcher's own error to report, not this script's --
    duplicating it would produce two different messages for one problem."""
    monkeypatch.setattr(approver, "CONFIG", _config(tmp_path, [], [FINGERPRINT]))
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(sys, "argv", ["approve_api_key.py", "--check"])
    assert approver.main() == 0
    assert capsys.readouterr().out == ""


def test_check_does_not_write(tmp_path, monkeypatch):
    """--check runs unattended on every launch; it must never mutate config."""
    config = _config(tmp_path, [], [FINGERPRINT])
    before = config.read_text(encoding="utf-8")
    _run_check(tmp_path, monkeypatch, rejected=[FINGERPRINT])
    assert config.read_text(encoding="utf-8") == before
    assert list(tmp_path.glob(".claude.json.bak-*")) == []


# --- the launcher wiring -----------------------------------------------------


def test_launcher_runs_the_preflight():
    """claude-env.ps1 is deployed into every project and is the only place the
    key is loaded, so it is the only place this check can run."""
    script = (ROOT / "claude-env.ps1").read_text(encoding="utf-8")
    assert "approve_api_key.py" in script
    assert "--check" in script


def test_the_fixer_is_deployed_to_target_projects():
    """The check is useless if the script it names is not there to run. This
    was the original failure: the fixer lived only in Solo-Code-CLI."""
    from tools import deploy
    assert deploy.should_copy(Path("tools") / "approve_api_key.py") is True
