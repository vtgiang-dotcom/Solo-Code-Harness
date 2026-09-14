#!/usr/bin/env python3
"""
Codex Guard Tests
=================
Runs tools/codex_guard.py as a subprocess and asserts the block/allow decision
(exit code 2 = block, 0 = allow).

Codex CLI has no project hook API, so codex_guard.py is the only automated
preflight between a Codex-issued command and the filesystem. The predicates it
delegates to (.claude/hooks/guard.py) are covered by test_claude_guard.py; what
these tests pin is the wiring in codex_guard itself -- that each input mode
reaches the right predicate and that a block is reported as exit 2.

Usage:
    python -m pytest tools/test_codex_guard.py -v
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GUARD = ROOT / "tools" / "codex_guard.py"

# Two secret shapes, because guard.py's patterns treat them differently.
# `generic_api_key` only fires on a QUOTED value, so a shell-style bare
# `KEY=value` trips nothing unless the token carries a recognised prefix
# (anthropic_key / openai_project_key). See SECRET_PATTERNS in guard.py.
# These are fixtures for the detector under test, not credentials.
_ANTHROPIC_SECRET = "sk-ant-abcdefghijklmnopqrstuvwxyz0123"  # noqa: S105
_QUOTED_SECRET = "sk-abcdefghijklmnopqrstuvwxyz123456"  # noqa: S105


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    """Invoke codex_guard, returning the completed process."""
    return subprocess.run(  # noqa: S603 — fixed argv, no shell
        [sys.executable, str(GUARD), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    "command",
    ["git status", "python -m pytest tools/ -q", "ls tools"],
)
def test_benign_command_is_allowed(command: str) -> None:
    """Ordinary repo commands must pass, or the gate gets disabled."""
    result = _run("--command", command)
    assert result.returncode == 0, f"unexpectedly blocked: {result.stderr}"


@pytest.mark.parametrize(
    "command",
    ["rm -rf /", "rm -rf /tmp/anything", "DROP TABLE users"],
)
def test_destructive_command_is_blocked(command: str) -> None:
    """Destructive commands exit 2 so a wrapper can refuse to run them."""
    result = _run("--command", command)
    assert result.returncode == 2, f"not blocked: {command!r}"
    assert "BLOCKED" in result.stderr


def test_secret_in_command_is_blocked() -> None:
    """A credential must be caught even in a bare shell `KEY=value` form."""
    result = _run("--command", f"export ANTHROPIC_API_KEY={_ANTHROPIC_SECRET}")
    assert result.returncode == 2
    assert "BLOCKED" in result.stderr


def test_secret_in_content_is_blocked() -> None:
    """Content mode is the file-write path; a secret there must block."""
    result = _run("--content", f'api_key = "{_QUOTED_SECRET}"')
    assert result.returncode == 2
    assert "BLOCKED" in result.stderr


def test_benign_content_is_allowed() -> None:
    """Ordinary source text must pass content mode."""
    result = _run("--content", "def add(a, b):\n    return a + b\n")
    assert result.returncode == 0, f"unexpectedly blocked: {result.stderr}"


def test_command_and_content_are_mutually_exclusive() -> None:
    """Exactly one input mode must be supplied."""
    result = _run("--command", "git status", "--content", "x")
    assert result.returncode != 0
    # argparse exits 2 for usage errors; the security block also uses 2, so
    # assert on the message that distinguishes them.
    assert "BLOCKED" not in result.stderr


def test_requires_an_input_mode() -> None:
    """Calling with neither mode is a usage error, not a silent allow."""
    result = _run()
    assert result.returncode != 0
    assert "BLOCKED" not in result.stderr
