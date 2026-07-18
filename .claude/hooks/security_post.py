#!/usr/bin/env python3
"""
security_post (Claude Code hook) — PostToolUse git-diff secret scan.

Python port of .kilo/hooks/post-tool-use/security-check-post.js. Stdlib-only.

Wired via .claude/settings.json:
    "PostToolUse": [ { "matcher": "Bash",
        "hooks": [ { "type": "command",
            "command": "python .claude/hooks/security_post.py" } ] } ]

Behavior:
  - Reads the PostToolUse JSON from stdin.
  - Only acts when the Bash command was a `git commit` or `git push`.
  - Scans the added (+) lines of `git diff HEAD` for high-sensitivity secrets.
  - Reports findings to stderr with the secret REDACTED. ALWAYS exits 0
    (advisory — never blocks; the pre-commit guard is the blocking layer).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

HIGH_SENSITIVITY_SECRETS: list[tuple[str, re.Pattern[str]]] = [
    ("Anthropic/OpenAI API key", re.compile(r"sk-[a-zA-Z0-9]{20,}")),
    ("AWS Access Key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GitHub Token", re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,}")),
    ("Google API Key", re.compile(r"AIza[0-9A-Za-z\-_]{35}")),
    ("Slack Token", re.compile(r"xox[bpras]-[0-9a-zA-Z]{10,}")),
    ("Private Key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
    ("Hardcoded password", re.compile(r"(?:password|passwd|pwd)\s*[:=]\s*[\"'][^\"']{8,}[\"']", re.I)),
    ("Hardcoded API key", re.compile(r"(?:api_key|apikey|api-key|secret_key)\s*[:=]\s*[\"'][\w\-]{20,}[\"']", re.I)),
    ("JWT Token", re.compile(r"eyJ[a-zA-Z0-9\-_]+\.eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+")),
    ("DB connection string", re.compile(r"(?:mongodb|postgres|mysql|redis)://[^\"'\s]+@", re.I)),
]


def scan_diff() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return []
    if result.returncode != 0 or not result.stdout.strip():
        return []

    findings: list[str] = []
    for i, line in enumerate(result.stdout.split("\n"), 1):
        if not line.startswith("+") or line.startswith("+++"):
            continue
        for name, pattern in HIGH_SENSITIVITY_SECRETS:
            if pattern.search(line):
                sanitized = pattern.sub("[REDACTED]", line)[:120]
                findings.append(f"  [{name}] line {i}: {sanitized}")
                break
    return findings


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if payload.get("tool_name", "") != "Bash":
        return 0

    command = (payload.get("tool_input", {}) or {}).get("command", "") or ""
    is_commit = re.search(r"\bgit\s+commit\b", command) is not None
    is_push = re.search(r"\bgit\s+push\b", command) is not None
    if not (is_commit or is_push):
        return 0

    try:
        findings = scan_diff()
    except Exception:  # noqa: BLE001 — advisory hook must never crash
        return 0

    if findings:
        op = "commit" if is_commit else "push"
        sys.stderr.write(
            f"\n[SecurityCheck] SECURITY ALERT after {op}:\n"
            + "\n".join(findings)
            + "\n  Remove hardcoded secrets and use environment variables.\n\n"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
