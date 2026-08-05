#!/usr/bin/env python3
"""
Security Scanner
=================
Scans codebase for common security issues: hardcoded secrets,
unsafe patterns, and misconfigurations.

Usage:
    python .github/scripts/security_scan.py <project_path>
    python .github/scripts/security_scan.py . --strict
"""

import re
import subprocess  # noqa: S404 — runs `git ls-files` on the scanned path only
import sys
from pathlib import Path

# Patterns to flag
SECRET_PATTERNS = [
    (r'(?:api_key|apikey|api-key)\s*[:=]\s*["\'][\w\-]{20,}["\']', "Hardcoded API key"),
    (r'(?:password|passwd)\s*[:=]\s*["\'][^"\']+["\']', "Hardcoded password"),
    (r'(?:secret|token)\s*[:=]\s*["\'][\w\-]{20,}["\']', "Hardcoded secret/token"),
    (r"sk-[a-zA-Z0-9]{20,}", "OpenAI/Anthropic API key pattern"),
    (r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----", "Private key in source"),
    (
        r'(?:mongodb|postgres|mysql)://[^"\']+@',
        "Database connection string with credentials",
    ),
    (
        r"eyJ[a-zA-Z0-9\-_]+\.eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+",
        "JWT token (possible hardcoded)",
    ),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
    (r"gh[p|o|u|s|r]_[A-Za-z0-9_]{36,255}", "GitHub Token"),
    (r"github_pat_[A-Za-z0-9_]{22,}", "GitHub fine-grained PAT"),
    (r"AIza[0-9A-Za-z\-_]{35}", "Google API Key"),
    (r"xox[bpras]-[0-9a-zA-Z]{10,}", "Slack Token"),
    # Prefixed-token formats. The generic `sk-[a-zA-Z0-9]{20,}` above stops at
    # the first "-", so it never matched sk-ant-/sk-proj- keys -- including
    # this project's own Anthropic key format. Length floors are set above
    # doc-placeholder length (e.g. "sk-ant-xxxxxxxxxxxx") to avoid firing on
    # README examples. Pinned by tools/test_secret_patterns.py.
    (r"sk-ant-[A-Za-z0-9\-_]{24,}", "Anthropic API key"),
    (r"sk-proj-[A-Za-z0-9\-_]{20,}", "OpenAI project key"),
    (r"npm_[A-Za-z0-9]{36}", "npm access token"),
    (r"glpat-[A-Za-z0-9\-_]{20,}", "GitLab personal access token"),
    (r"dop_v1_[A-Za-z0-9]{64}", "DigitalOcean token"),
    # Authorization headers carry no quotes and no "=", so the quoted
    # secret/token pattern above never saw them.
    (r"Bearer\s+[A-Za-z0-9._\-+/=]{20,}", "Bearer token in Authorization header"),
]

UNSAFE_PATTERNS = [
    (r"\.innerHTML\s*=", "Unsafe innerHTML assignment (XSS risk)"),
    (r"eval\(", "Use of eval() — code injection risk"),
    (r"exec\(", "Use of exec() — code injection risk"),
    (r"os\.system\(", "Use of os.system() — command injection risk"),
    (
        r"subprocess\.call\(.*shell\s*=\s*True",
        "Shell=True in subprocess — injection risk",
    ),
    (r"document\.write\(", "document.write() — XSS risk"),
    (r"dangerouslySetInnerHTML", "React dangerouslySetInnerHTML — XSS risk"),
    (r"bypassSecurityTrust", "Angular bypassSecurityTrust — XSS risk"),
]

SKIP_DIRS = {
    "node_modules",
    "__pycache__",
    ".next",
    "dist",
    "build",
    ".venv",
    "venv",
    ".cache",
    ".git",
    ".hg",
    ".svn",
    ".tox",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
}
# Files git-ignored in this repo — skip to avoid flagging local dev secrets
SKIP_NAMES: set[str] = {".env"}
SKIP_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".map",
    ".lock",
    ".min.js",
    ".min.css",
    ".pyc",
}


def untracked_top_level_dirs(root: Path) -> set[str]:
    """Top-level directories inside `root` containing zero git-tracked files.

    Reference repos (unpacked upstream projects kept alongside the harness for
    study) contain no tracked files; every harness directory contains many.
    Using that signal instead of a hardcoded name list means a newly unpacked
    repo is excluded the moment it lands -- the previous list named 17 repos,
    all of which had since been deleted, while the one repo actually present
    was absent from it and pushed the gate to 248 false positives.

    Deliberately NOT `git ls-files --others --directory`: that reports any
    directory holding untracked files, which collapses to the whole directory
    and would have excluded `.claude`, `.github`, and `tools` -- silencing the
    gate over most of the harness.

    Returns an empty set when `root` is not a git repo (this script is also run
    against arbitrary external paths), so scanning degrades to "check
    everything" rather than silently skipping real findings.
    """
    try:
        proc = subprocess.run(  # noqa: S603,S607 — fixed argv, no shell
            ["git", "-C", str(root), "ls-files"],
            capture_output=True, text=True, timeout=60, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    if proc.returncode != 0:
        return set()

    tracked_top_level = {
        line.split("/")[0] for line in proc.stdout.splitlines() if "/" in line
    }
    return {
        entry.name
        for entry in root.iterdir()
        if entry.is_dir() and entry.name not in tracked_top_level
    }


def should_skip(file_path: Path, extra_skip_dirs: frozenset[str] = frozenset()) -> bool:
    # Skip files that intentionally contain mock secrets for testing
    name = file_path.name.lower()
    if name in {"eval_harness.py", "secret-scan.test.js", "guard.test.js", "test_claude_guard.py", "test_secret_patterns.py"}:
        return True
    if name in SKIP_NAMES:
        return True
    parts = file_path.parts
    for part in parts:
        if part in SKIP_DIRS or part in extra_skip_dirs:
            return True
    return file_path.suffix.lower() in SKIP_EXTENSIONS


def scan_file(file_path: Path, strict: bool) -> list[tuple[str, str, int]]:
    findings = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings

    for line_no, line in enumerate(content.splitlines(), 1):
        for pattern, description in SECRET_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                findings.append((str(file_path), f"SECRET: {description}", line_no))
        if strict:
            for pattern, description in UNSAFE_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append((str(file_path), f"UNSAFE: {description}", line_no))
    return findings


def main():
    strict = "--strict" in sys.argv
    project_path = Path(
        sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "."
    ).resolve()

    if not project_path.exists():
        print(f"Path not found: {project_path}")
        sys.exit(1)

    print(f"Scanning: {project_path}")
    print(f"Mode: {'STRICT' if strict else 'SECRETS ONLY'}\n")

    reference_dirs = frozenset(untracked_top_level_dirs(project_path))
    if reference_dirs:
        print(f"Skipping untracked reference dirs: {', '.join(sorted(reference_dirs))}\n")

    all_findings = []
    file_count = 0
    for file_path in project_path.rglob("*"):
        if file_path.is_file() and not should_skip(file_path, reference_dirs):
            file_count += 1
            findings = scan_file(file_path, strict)
            all_findings.extend(findings)

    print(f"Files scanned: {file_count}")

    if all_findings:
        print(f"\nFindings: {len(all_findings)}\n")
        for file_path, desc, line in all_findings:
            print(f"  [{desc}] {file_path}:{line}")
        print(f"\n{len(all_findings)} issue(s) found.")
        sys.exit(1)
    else:
        print("No issues found.")
        sys.exit(0)


if __name__ == "__main__":
    main()
