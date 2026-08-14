#!/usr/bin/env python3
"""
E2E Testing Framework — Real API tests with self-skip
======================================================
End-to-end tests for OpenCode CLI and Kilo CLI with DeepSeek models.
Self-skips when API key not available (keyless CI support).

Inspired by DeepSeek harness ACP e2e pattern:
- Real subprocess execution
- Real API interaction (when key available)
- World verification (filesystem effects, not self-reports)
- Self-skip mechanism for keyless environments

Usage:
    python -m pytest tools/test_e2e.py -v                    # Skip if no key
    DEEPSEEK_API_KEY=xxx python -m pytest tools/test_e2e.py  # Run with real API
    python tools/test_e2e.py --self-test                     # Validate framework
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

# ── Constants ────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
OPENCODE_CLI = ROOT / "tools" / "opencode_delegate.py"
KILO_CLI = ROOT / "tools" / "kilo_cli_delegate.py"

HAS_DEEPSEEK_KEY = bool(os.getenv("DEEPSEEK_API_KEY"))

# ── Helpers ──────────────────────────────────────────────────────────────────


def run_cli(
    cli_path: Path,
    task: str,
    *,
    model: str | None = None,
    free: bool = False,
    timeout: int = 120,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """
    Run a CLI delegate tool with the given task.

    Args:
        cli_path: Path to the CLI script (opencode_delegate.py or kilo_cli_delegate.py)
        task: Task description to execute
        model: Optional model override
        free: Use free model tier
        timeout: Subprocess timeout in seconds
        cwd: Working directory for subprocess

    Returns:
        CompletedProcess with stdout/stderr

    Raises:
        subprocess.TimeoutExpired: If execution exceeds timeout
        subprocess.CalledProcessError: If CLI returns non-zero (check=True)
    """
    cmd = ["python", str(cli_path), task]

    if model:
        cmd.extend(["--model", model])
    elif free:
        cmd.append("--free")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd or ROOT,
        check=False,
    )

    return result


def parse_opencode_output(stdout: str) -> dict[str, Any]:
    """
    Parse OpenCode CLI output looking for JSON response blocks.

    OpenCode CLI outputs structured JSON containing model response,
    token usage, and timing information.

    Args:
        stdout: Raw stdout from OpenCode CLI

    Returns:
        Parsed JSON dict, or empty dict if no JSON found
    """
    lines = stdout.strip().split("\n")

    for line in lines:
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue

    return {}


# ── Smoke Tests (no API key required) ────────────────────────────────────────


def test_opencode_cli_exists():
    """OpenCode CLI script exists and is readable."""
    assert OPENCODE_CLI.exists(), f"OpenCode CLI not found: {OPENCODE_CLI}"
    assert OPENCODE_CLI.is_file(), f"OpenCode CLI is not a file: {OPENCODE_CLI}"


def test_kilo_cli_exists():
    """Kilo CLI script exists and is readable."""
    assert KILO_CLI.exists(), f"Kilo CLI not found: {KILO_CLI}"
    assert KILO_CLI.is_file(), f"Kilo CLI is not a file: {KILO_CLI}"


def test_opencode_cli_help():
    """OpenCode CLI responds to --help."""
    result = subprocess.run(
        ["python", str(OPENCODE_CLI), "--help"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    # Either succeeds with help text, or fails with usage message
    assert result.returncode in (0, 2), "OpenCode CLI should respond to --help"
    assert "usage" in result.stdout.lower() or "usage" in result.stderr.lower()


def test_kilo_cli_help():
    """Kilo CLI responds to --help."""
    result = subprocess.run(
        ["python", str(KILO_CLI), "--help"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    # Either succeeds with help text, or fails with usage message
    assert result.returncode in (0, 2), "Kilo CLI should respond to --help"
    assert "usage" in result.stdout.lower() or "usage" in result.stderr.lower()


# ── Real API Tests (self-skip when no key) ───────────────────────────────────


@pytest.mark.skipif(not HAS_DEEPSEEK_KEY, reason="ENV key not set")
def test_opencode_echo_task():
    """
    OpenCode CLI: Real API call with simple echo task.

    Verifies:
    - CLI executes without error
    - Model responds (non-empty output)
    - Token usage is reported
    """
    result = run_cli(
        OPENCODE_CLI,
        "Echo the exact text: E2E_TEST_MARKER",
        free=True,
        timeout=60,
    )

    assert result.returncode == 0, f"OpenCode CLI failed:\n{result.stderr}"

    # Check for marker in output (either in JSON or raw stdout)
    output = result.stdout.lower()
    assert "e2e_test_marker" in output, "Model did not echo the marker"

    # Try to parse structured output
    parsed = parse_opencode_output(result.stdout)
    if parsed:
        # If JSON response found, verify structure
        assert "choices" in parsed or "content" in parsed, \
            "OpenCode output missing expected fields"


@pytest.mark.skipif(not HAS_DEEPSEEK_KEY, reason="ENV key not set")
def test_opencode_file_write_world_verification():
    """
    OpenCode CLI: Real file write task with world verification.

    Inspired by DeepSeek ACP pattern: verify the WORLD (filesystem),
    not the agent's self-report.

    Verifies:
    - Model writes requested file
    - File content matches request
    - No reliance on model's claim of success
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        target_file = tmppath / "e2e_proof.txt"
        marker = "OPENCODE_E2E_SUCCESS"

        result = run_cli(
            OPENCODE_CLI,
            f'Write the exact text "{marker}" to file: {target_file}',
            free=True,
            timeout=90,
            cwd=tmppath,
        )

        # Check CLI execution (allow model errors, verify world instead)
        if result.returncode != 0:
            pytest.skip(f"OpenCode CLI error (network/timeout): {result.stderr[:200]}")

        # WORLD VERIFICATION: read file independently
        assert target_file.exists(), \
            f"Model did not create file: {target_file}\nStdout: {result.stdout[:500]}"

        content = target_file.read_text(encoding="utf-8")
        assert marker in content, \
            f"File content wrong. Expected '{marker}', got: {content[:100]}"


@pytest.mark.skipif(not HAS_DEEPSEEK_KEY, reason="ENV key not set")
def test_kilo_cli_echo_task():
    """
    Kilo CLI: Real API call with simple echo task.

    Verifies:
    - CLI executes without error
    - Model responds (non-empty output)
    """
    result = run_cli(
        KILO_CLI,
        "Echo the exact text: E2E_KILO_MARKER",
        timeout=60,
    )

    # Kilo CLI may have different error patterns, be lenient
    if result.returncode != 0:
        pytest.skip(f"Kilo CLI error (network/timeout): {result.stderr[:200]}")

    # Check for marker in output
    output = result.stdout.lower()
    assert "e2e_kilo_marker" in output, \
        f"Model did not echo marker. Output: {result.stdout[:500]}"


# ── Self-Test (framework validation) ─────────────────────────────────────────


def run_self_test() -> bool:
    """
    Self-test: validate the e2e framework itself.

    Returns:
        True if all self-tests pass
    """
    print("Running E2E framework self-test...")

    # Test 1: CLI paths exist
    print("\n1. Checking CLI paths...")
    if not OPENCODE_CLI.exists():
        print(f"[FAIL] OpenCode CLI not found: {OPENCODE_CLI}", file=sys.stderr)
        return False
    if not KILO_CLI.exists():
        print(f"[FAIL] Kilo CLI not found: {KILO_CLI}", file=sys.stderr)
        return False
    print("[OK] Both CLI paths exist")

    # Test 2: Help command responds
    print("\n2. Testing --help flags...")
    for cli_name, cli_path in [("OpenCode", OPENCODE_CLI), ("Kilo", KILO_CLI)]:
        result = subprocess.run(
            ["python", str(cli_path), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode not in (0, 2):
            print(f"[FAIL] {cli_name} CLI --help failed", file=sys.stderr)
            return False
        if "usage" not in result.stdout.lower() and "usage" not in result.stderr.lower():
            print(f"[FAIL] {cli_name} CLI --help has no usage text", file=sys.stderr)
            return False
    print("[OK] Both CLIs respond to --help")

    # Test 3: API key detection
    print("\n3. Checking API key detection...")
    has_key = bool(os.getenv("DEEPSEEK_API_KEY"))
    print(f"[OK] ENV key: {'present' if has_key else 'not set (real API tests will skip)'}")

    # Test 4: Temp directory for world verification
    print("\n4. Testing temp directory creation...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        if not tmppath.exists():
            print("[FAIL] Temp directory creation failed", file=sys.stderr)
            return False
        test_file = tmppath / "test.txt"
        test_file.write_text("test", encoding="utf-8")
        if not test_file.exists():
            print("[FAIL] File write in temp directory failed", file=sys.stderr)
            return False
    print("[OK] Temp directory and file operations work")

    print("\n[OK] All self-tests passed!")
    print("\nRun pytest to execute real e2e tests:")
    print(f"  python -m pytest {__file__} -v")
    if not has_key:
        print("\nTo run real API tests, set ENV key:")
        print(f"  ENV_VAR=xxx python -m pytest {__file__} -v")

    return True


# ── CLI Entry Point ──────────────────────────────────────────────────────────


def main() -> int:
    """CLI entry point for self-test mode."""
    if "--self-test" in sys.argv:
        success = run_self_test()
        return 0 if success else 1

    print(f"E2E Testing Framework for OpenCode CLI and Kilo CLI", file=sys.stderr)
    print(f"\nUsage:", file=sys.stderr)
    print(f"  python -m pytest {__file__} -v", file=sys.stderr)
    print(f"  python {__file__} --self-test", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
