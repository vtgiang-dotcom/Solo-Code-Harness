#!/usr/bin/env python3
"""
Secret Pattern Coverage Tests (cross-scanner)
=============================================
This harness has THREE independent secret detectors, each a separate
hand-maintained copy of the same pattern list:

  1. .claude/hooks/guard.py            -- PreToolUse, blocks the write (exit 2)
  2. .kilo/hooks/pre-tool-use/secret-scan.js -- Kilo PreToolUse equivalent
  3. .github/scripts/security_scan.py  -- CI gate, blocks the merge (exit 1)

Nothing structurally forced them to agree, and they drifted: a token format
added to one was not added to the others. Worse, all three shared the same
blind spots -- every modern prefixed-token format (sk-ant-, sk-proj-, npm_,
glpat-, dop_v1_) and the Authorization: Bearer header form passed all three
untouched, including this project's own Anthropic API key format.

These tests pin ONE corpus against ALL THREE scanners, so a format can never
again be covered by one detector and missed by the others. Every MUST_DETECT
entry was verified failing on all three before the patterns were fixed.

Usage:
    python -m pytest tools/test_secret_patterns.py -v
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GUARD = ROOT / ".claude" / "hooks" / "guard.py"
SECRET_SCAN_JS = ROOT / ".kilo" / "hooks" / "pre-tool-use" / "secret-scan.js"

sys.path.insert(0, str(ROOT / ".github" / "scripts"))
from security_scan import SECRET_PATTERNS as CI_PATTERNS  # noqa: E402

# ── Shared corpus ────────────────────────────────────────────────────────
# Synthetic values: correct SHAPE, never a real credential. Each entry is
# (id, sample_line). The `id` doubles as the pytest test id.
MUST_DETECT: list[tuple[str, str]] = [
    # The format this project itself uses -- missed by all 3 scanners because
    # `sk-[a-zA-Z0-9]{20,}` does not cross the "-" in "sk-ant-".
    ("anthropic_sk_ant", 'ANTHROPIC_API_KEY=sk-ant-api03-AbCdEf1234567890AbCdEf1234567890AbCdEfGh'),
    ("openai_sk_proj", 'OPENAI_API_KEY=sk-proj-AbCdEf1234567890AbCdEfGhIjKl'),
    # Bearer in an HTTP header has no quotes and no "=", so the quoted
    # `hardcoded_token` pattern never matched it.
    ("bearer_header", 'curl -H "Authorization: Bearer AbCdEf1234567890AbCdEfGhIjKl" https://api.example.com'),
    ("npm_token", 'NPM_TOKEN=npm_AbCdEf1234567890AbCdEf1234567890abcd'),
    ("gitlab_pat", 'CI_TOKEN=glpat-AbCdEf1234567890AbCd'),
    ("github_fine_grained", 'GITHUB_TOKEN=github_pat_11ABCDEFG0AbCdEf1234567890AbCdEf1234567890'),
    ("digitalocean", 'DO_TOKEN=dop_v1_' + 'a' * 64),
    # Regression guards -- these already worked; they must keep working.
    ("aws_access_key", 'AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE'),
    ("google_api_key", 'GOOGLE_KEY=AIzaSyA1234567890abcdefghijklmnopqrstuv'),
    ("slack_token", 'SLACK=xoxb-1234567890-AbCdEfGhIjKl'),
    ("private_key_pem", '-----BEGIN RSA PRIVATE KEY-----'),
]

# Lines that must NOT trip any scanner. A detector that cries wolf gets
# switched off, so false positives cost more than misses (SPEC 7.2.1).
MUST_NOT_DETECT: list[tuple[str, str]] = [
    ("prose_about_keys", "Store the API key in an environment variable, never in source."),
    ("short_placeholder", 'api_key = "TODO"'),
    ("env_var_reference", 'api_key = os.environ["ANTHROPIC_API_KEY"]'),
    ("sk_prefixed_word", "The sketch-utils module handles rendering."),
    ("bearer_prose", "Send the token as a Bearer credential in the header."),
    ("npm_install", "npm_config_registry is set by the CI runner."),
    ("markdown_placeholder", "ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx"),
]


def _ci_scan(line: str) -> list[str]:
    """Run the CI scanner's patterns exactly as scan_file() does."""
    return [
        desc for pattern, desc in CI_PATTERNS
        if re.search(pattern, line, re.IGNORECASE)
    ]


def _run_guard(payload: dict) -> int:
    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    return proc.returncode


def _run_secret_scan_js(content: str, file_path: str = "config.yml") -> int:
    """Invoke the Kilo secret-scan hook. Uses a secret-prone extension so a
    finding escalates to exit 2 (block) rather than a warning."""
    payload = {"tool_name": "Write", "tool_input": {"file_path": file_path, "content": content}}
    proc = subprocess.run(
        ["node", str(SECRET_SCAN_JS)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    return proc.returncode


# ── 1. CI gate: .github/scripts/security_scan.py ─────────────────────────


@pytest.mark.parametrize("sample_id,line", MUST_DETECT, ids=[s[0] for s in MUST_DETECT])
def test_ci_scanner_detects(sample_id, line):
    assert _ci_scan(line), f"security_scan.py missed {sample_id}: {line[:60]}"


@pytest.mark.parametrize("sample_id,line", MUST_NOT_DETECT, ids=[s[0] for s in MUST_NOT_DETECT])
def test_ci_scanner_no_false_positive(sample_id, line):
    hits = _ci_scan(line)
    assert not hits, f"security_scan.py false-positive on {sample_id}: {hits}"


# ── 2. Claude PreToolUse gate: .claude/hooks/guard.py ────────────────────


@pytest.mark.parametrize("sample_id,line", MUST_DETECT, ids=[s[0] for s in MUST_DETECT])
def test_guard_blocks_secret_in_content(sample_id, line):
    payload = {"tool_name": "Write", "tool_input": {"file_path": "config.py", "content": line}}
    assert _run_guard(payload) == 2, f"guard.py allowed a write containing {sample_id}"


@pytest.mark.parametrize("sample_id,line", MUST_NOT_DETECT, ids=[s[0] for s in MUST_NOT_DETECT])
def test_guard_allows_non_secret(sample_id, line):
    payload = {"tool_name": "Write", "tool_input": {"file_path": "notes.md", "content": line}}
    assert _run_guard(payload) == 0, f"guard.py false-blocked {sample_id}"


# ── 3. Kilo PreToolUse gate: .kilo/hooks/pre-tool-use/secret-scan.js ─────


@pytest.mark.parametrize("sample_id,line", MUST_DETECT, ids=[s[0] for s in MUST_DETECT])
def test_kilo_secret_scan_blocks(sample_id, line):
    assert _run_secret_scan_js(line) == 2, f"secret-scan.js allowed {sample_id}"


@pytest.mark.parametrize("sample_id,line", MUST_NOT_DETECT, ids=[s[0] for s in MUST_NOT_DETECT])
def test_kilo_secret_scan_allows(sample_id, line):
    assert _run_secret_scan_js(line) == 0, f"secret-scan.js false-blocked {sample_id}"


# ── 4. Cross-scanner parity invariant ────────────────────────────────────


@pytest.mark.parametrize("sample_id,line", MUST_DETECT, ids=[s[0] for s in MUST_DETECT])
def test_all_three_scanners_agree(sample_id, line):
    """The drift that caused this file: a format covered by one detector and
    missed by another. Pin agreement, not just individual coverage."""
    verdicts = {
        "security_scan.py": bool(_ci_scan(line)),
        "guard.py": _run_guard(
            {"tool_name": "Write", "tool_input": {"file_path": "config.py", "content": line}}
        ) == 2,
        "secret-scan.js": _run_secret_scan_js(line) == 2,
    }
    missed = [name for name, caught in verdicts.items() if not caught]
    assert not missed, f"{sample_id} caught by some scanners but missed by: {missed}"
