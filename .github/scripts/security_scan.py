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
    (r"AIza[0-9A-Za-z\-_]{35}", "Google API Key"),
    (r"xox[bpras]-[0-9a-zA-Z]{10,}", "Slack Token"),
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
    "ECC-main",                    # Reference project — not part of harness
    "agents-main",                 # Reference project — not part of harness
    "awesome-deepseek-agent-main", # Reference project — DeepSeek integration guides
    "claude-code-main",            # Reference project — official Claude Code repo
    "skills-main",                 # Reference project — official Anthropic skills
    "claw-code-main",              # Reference project — Claw Code autonomous agent
    "claude-plugins-official-main",# Reference project — official plugin marketplace
    "skills-main-2",               # Reference project — Microsoft Azure skills
    "gemini-skills-main",          # Reference project — Gemini skills
    "code",                        # Reference project root — all external code
    "hermes-agent-main",          # Reference project — Hermes agent analysis
    "deer-flow-main",             # Reference project — DeerFlow 2.0 patterns
    "opencode-dev",               # OpenCode source — third-party, not harness code
    "Solo-Code-Harness",          # SoloC-Harness worktree — third-party, not harness code
    "codebase-memory-mcp-main",   # Reference project — C MCP server for codebase memory
    "cocoindex-code-main",        # Reference project — Rust-based code indexing tool
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


def should_skip(file_path: Path) -> bool:
    # Skip files that intentionally contain mock secrets for testing
    name = file_path.name.lower()
    if name in {"eval_harness.py", "secret-scan.test.js", "guard.test.js"}:
        return True
    if name in SKIP_NAMES:
        return True
    parts = file_path.parts
    for part in parts:
        if part in SKIP_DIRS:
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

    all_findings = []
    file_count = 0
    for file_path in project_path.rglob("*"):
        if file_path.is_file() and not should_skip(file_path):
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
