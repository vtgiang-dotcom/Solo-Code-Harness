#!/usr/bin/env python3
"""
Boundary Audit — Phát hiện file project lạc vào thư mục harness
==============================================================

Sau khi deploy harness vào project đích, script này quét các thư mục
harness để đảm bảo không có file project (code của dự án thực) vô tình
bị copy vào thư mục harness infrastructure.

Usage:
    python .github/scripts/boundary_audit.py .
    python .github/scripts/boundary_audit.py . --strict
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# ─── Harness directories ───────────────────────────────────────────────────
HARNESS_DIRS = [
    ".kilo",
    ".copilot",
    ".gemini",
    ".claude",
    ".claude-plugin",
    ".github",
    ".contracts",
    ".vscode",
    "tools",
]

# ─── Allowed file extensions IN harness dirs ────────────────────────────────
# Only these extensions are legitimate in harness infrastructure.
HARNESS_ALLOWED_EXTENSIONS = {
    ".md",       # Documentation, instructions, skills, agents
    ".json",     # Configs, state, hooks
    ".jsonc",    # Configs with comments
    ".js",       # Hooks, plugins
    ".mjs",      # ES modules (tests)
    ".py",       # Scripts (security_scan, checklist, garden, deploy, etc.)
    ".toml",     # Configs (.ruff.toml, .gitleaks.toml)
    ".txt",      # Allowlists, skip lists
    ".yaml",     # Agent config
    ".yml",      # CI config
    ".ps1",      # PowerShell scripts
    ".sh",       # Shell scripts
    ".lock",     # Package lock files, .harness.lock
    ".jsonl",    # Log files
    ".sql",      # Schema docs (tools/shared_state_schema.sql)
    ".template", # Env templates (.env.template)
    ".gitignore",# Git ignore
    ".gitkeep",  # Git keep
    ".prompt.md",# Copilot prompts
    "",          # No extension (executables, .solocode marker)
}

# ─── Files that are explicitly allowed despite unusual extension ────────────
HARNESS_ALLOWED_SPECIAL = {
    "Makefile",
    ".gitignore",
    ".solocode",
    ".harness.lock",
    ".DS_Store",
    "Thumbs.db",
}

# ─── Directories that are always allowed in harness (not counted as project) ─
HARNESS_KNOWN_SUBDIRS = {
    "node_modules",       # Plugin dependencies
    ".git",               # Git repository
    "__pycache__",        # Python cache
    ".pytest_cache",      # Test cache
    ".ruff_cache",        # Lint cache
    "dist",               # Build output
    "build",              # Build output
    ".venv",              # Virtual environment
    "venv",               # Virtual environment
}


def should_report(file_path: Path, root: Path, strict: bool = False) -> tuple[bool, str]:
    """Check if a file in a harness directory looks like project code.

    Returns (should_report: bool, reason: str).
    """
    name = file_path.name

    # Skip known harness subdirectories
    for part in file_path.parts:
        if part in HARNESS_KNOWN_SUBDIRS:
            return False, f"known harness subdir ({part})"

    # Skip files in allowlist
    if name in HARNESS_ALLOWED_SPECIAL:
        return False, "explicitly allowed"

    # Check extension
    suffix = file_path.suffix
    # Handle double extensions like .prompt.md → check ".md" part
    if suffix == ".md" and ".prompt" in name:
        return False, "prompt markdown"
    if suffix == ".lock":
        return False, "lock file"

    if suffix in HARNESS_ALLOWED_EXTENSIONS:
        if not strict:
            return False, f"allowed extension ({suffix})"
        # In strict mode, also check if the file looks like project code
        if suffix in (".js", ".py") and file_path.stat().st_size > 1000:
            # Check first 200 chars for harness markers
            first_bytes = file_path.read_bytes()[:200]
            try:
                first_text = first_bytes.decode("utf-8")
                if "harness" in first_text.lower() or "#!/usr/bin/env" in first_text:
                    return False, "harness script"
                # Heuristic: if the file has imports/requires typical of app code
                if suffix == ".py" and ("from django" in first_text or "from flask" in first_text):
                    return True, "looks like app code (web framework imports)"
                if suffix == ".js" and ("react" in first_text.lower() or "express" in first_text.lower()):
                    return True, "looks like app code (framework imports)"
            except UnicodeDecodeError:
                pass
        return False, ""
    else:
        # Non-standard extension
        # Allow empty files (often markers)
        if file_path.stat().st_size == 0:
            return False, "empty file (marker)"
        return True, f"non-harness extension ({suffix})"


def audit(root: Path, strict: bool = False) -> tuple[list[str], list[str], list[str]]:
    """Audit harness directories for project code leakage.

    Returns (warnings, errors, info_lines).
    """
    warnings: list[str] = []
    errors: list[str] = []
    info: list[str] = []

    for d in HARNESS_DIRS:
        harness_dir = root / d
        if not harness_dir.is_dir():
            continue

        for file_path in harness_dir.rglob("*"):
            if file_path.is_dir():
                continue

            report, reason = should_report(file_path, root, strict=strict)

            if report:
                rel = file_path.relative_to(root)
                err_msg = f"[{d}/]  {rel}  —  {reason}"
                if strict:
                    errors.append(err_msg)
                else:
                    warnings.append(err_msg)
            elif reason:
                # Info: why it's allowed (useful for audit trails)
                pass  # Too verbose; only log in --verbose mode

    # Check root-level files that might be project code mistakenly copied
    for f in root.iterdir():
        if f.is_file() and f.name not in HARNESS_ALLOWED_SPECIAL and f.suffix not in HARNESS_ALLOWED_EXTENSIONS and f.name != ".harness.lock" and f.stat().st_size > 0:
            warnings.append(f"[ROOT]  {f.name}  —  non-harness extension ({f.suffix})")

    return warnings, errors, info


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit harness dirs for project code leakage"
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Target project directory (default: current directory)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict mode: raise errors (non-zero exit) on suspicious files",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show per-file verdict (why each file was allowed)",
    )
    args = parser.parse_args()

    target = Path(args.target).resolve()
    if not target.is_dir():
        print(f"[ERROR] Not a directory: {target}")
        return 1

    print(f"=== Boundary Audit: {target}")
    print(f"    Mode: {'STRICT' if args.strict else 'WARN-ONLY'}")
    print()

    warnings, errors, info = audit(target, strict=args.strict)

    if warnings:
        print("--- WARNINGS (suspicious files in harness dirs) ---")
        for w in warnings:
            print(f"  {w}")
        print()

    if errors:
        print("--- ERRORS (project code in harness dirs) ---")
        for e in errors:
            print(f"  {e}")
        print()

    total = len(warnings) + len(errors)
    if total == 0:
        print("Boundary clean — no project code found in harness directories.")
        return 0
    else:
        print(f"Found {total} issue(s): {len(warnings)} warning(s), {len(errors)} error(s)")
        print("These files may be project code that leaked into harness infrastructure.")
        print("Move them to appropriate project directories or delete if accidental.")
        return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
