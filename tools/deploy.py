#!/usr/bin/env python3
"""
deploy.py — Deploy or scaffold Solo-Code Harness for new/existing projects.

Two modes:
  scaffold   Create a NEW project with full harness (git init, copy files, validate)
  deploy     Copy harness into an EXISTING project directory

Usage:
    # Scaffold a new project (auto mode — target does not exist)
    python tools/deploy.py scaffold /path/to/new-project
    python tools/deploy.py scaffold /path/to/new-project --engine all
    python tools/deploy.py scaffold /path/to/new-project --name my-project

    # Deploy to an existing project
    python tools/deploy.py deploy /path/to/existing-project
    python tools/deploy.py deploy /path/to/existing-project --engine opencode
    python tools/deploy.py deploy /path/to/existing-project --dry-run

    # Auto-detect: scaffold if target missing, deploy if exists
    python tools/deploy.py /path/to/target

    # Interactive mode (no args)
    python tools/deploy.py
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════
# Deployment manifest — what to copy where
# ═══════════════════════════════════════════════════════════════════════

ROOT = Path(__file__).resolve().parent.parent

# Files to copy (relative to ROOT)
ROOT_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "opencode.json",
    "kilo.jsonc",
    ".mcp.json",
    ".gitleaks.toml",
    ".ruff.toml",
    ".pre-commit-config.yaml",
    "eslint.config.js",
    "pyproject.toml",
    "Makefile",
    "opencode.ps1",
    "SPEC.md",
    "verify.sh",
    "agent.yaml",
    "extensions_config.json",
    ".gitignore",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
]

# `.harness.lock` is NOT in ROOT_FILES — it is generated fresh
# for each scaffold/deploy with its own timestamp.

# Directories to copy (relative to ROOT)
DIRS_ALL = [
    ".opencode",
    ".kilo",
    ".copilot",
    ".gemini",
    ".claude",
    ".claude-plugin",
    ".github",
    ".vscode",
    ".contracts",
    "tools",
]

DIRS_OPENCODE = [
    ".opencode",
    ".github",
    ".contracts",
    "tools",
]

DIRS_COPILOT = [
    ".copilot",
    ".github",
    ".contracts",
    ".vscode",
    "tools",
]

DIRS_CLAUDE = [
    ".claude",
    ".claude-plugin",
    ".github",
    ".contracts",
    "tools",
]

# Patterns to exclude from copy
EXCLUDE_DIRS = {
    ".pytest_cache", ".ruff_cache", "node_modules", ".git",
    "__pycache__", ".venv", "venv",
    ".solocode", "cocoindex-code-main", "docs",
    # Runtime state directories — never belong in a deploy
    "sessions",           # .kilo/state/sessions/
    "logs",               # .kilo/logs/
}
EXCLUDE_FILES = {
    ".env", "usage.log", "usage.jsonl",
    ".DS_Store", "Thumbs.db",
    "settings.local.json",  # .claude/ personal overrides — never deploy
    # Runtime state files — never belong in a deploy
    "token-log.jsonl",    # .kilo/state/token-log.jsonl
    "tool-count.json",    # .kilo/state/tool-count.json
    "edited-files.json",  # .kilo/state/edited-files.json
}

# Default README template for scaffolded projects
README_TEMPLATE = """# {project_name}

> Scaffolded from [Solo-Code-CLI](https://github.com/Solo-Code-CLI) — AI agent harness with Kilo + OpenCode + Copilot + Gemini engines.

{description}

## Quick Start

```bash
# Install dependencies (if any)
pip install -e .          # Python project
# or
npm install               # Node project

# Generate harness artifacts
python tools/generate_harness.py --harness all

# Validate schemas
python tools/validate_schemas.py

# Run security scan
python .github/scripts/security_scan.py .

# Full verification
python .github/scripts/checklist.py .
```

## Verification Gates

| Gate | Command |
|------|---------|
| Security | `python .github/scripts/security_scan.py .` |
| Lint | `ruff check .` |
| Schema | `python tools/validate_schemas.py` |
| Garden | `python tools/garden.py` |
| Test | `python -m pytest tools/` |
| Full | `python .github/scripts/checklist.py .` |

## Engines

- **[Kilo](https://kilo.ai)** — hooks, skills, memory, orchestrators
- **[OpenCode](https://opencode.ai)** — agents, plugins, MCP servers
- **[Copilot](https://github.com/features/copilot)** — agents, skills, commands, prompts
- **[Gemini](https://gemini.google.com)** — additional AI assistant config

## Important: Harness Boundaries

This project was scaffolded with **Solo-Code Harness** — an AI agent discipline layer. Many files and directories in this project are harness infrastructure, NOT project source code. **Do not confuse them.**

| Contains | Purpose |
|----------|---------|
| `.kilo/`, `.opencode/`, `.copilot/`, `.gemini/` | AI agent rules, skills, hooks — NOT project logic |
| `.github/scripts/` | Verification scripts (`security_scan.py`, `checklist.py`) |
| `tools/` | Harness utilities (`deploy.py`, `garden.py`) |
| `.vscode/` | Harness IDE config — NOT project config |
| `AGENTS.md`, `kilo.jsonc`, `opencode.json`, `SPEC.md`, `.harness.lock` | Agent behavior configuration |

> **Read `.harness.lock`** for the authoritative boundary list. Never modify harness files to fix a project bug. Never modify project files to fix a harness issue.

## License

MIT
"""

HARNESS_LOCK_TEMPLATE = """# Solo-Code Harness Manifest
# ===========================
# File này đánh dấu ranh giới giữa harness infrastructure và code dự án.
# AI Model: đọc file này trước khi phân tích codebase.
#
# MỌI FILE/THƯ MỤC trong [boundaries] là HARNESS — KHÔNG phải code dự án.
# Không sửa, không phân tích như logic nghiệp vụ.

[harness]
version = "{version}"
source = "solo-code-io/solo-code-cli"
generated_at = "{timestamp}"

[boundaries]
# Thư mục harness — KHÔNG chứa code dự án
dirs = [
    ".kilo",
    ".opencode",
    ".copilot",
    ".gemini",
    ".claude",
    ".claude-plugin",
    ".github",
    ".contracts",
    ".vscode",
    "tools",
]

# File gốc harness — KHÔNG phải code dự án
files = [
    "AGENTS.md",
    "CLAUDE.md",
    "agent.yaml",
    "kilo.jsonc",
    "opencode.json",
    ".mcp.json",
    ".ruff.toml",
    ".gitleaks.toml",
    "Makefile",
    "pyproject.toml",
    "opencode.ps1",
    "verify.sh",
    "extensions_config.json",
    "SPEC.md",
    ".gitignore",
    ".pre-commit-config.yaml",
]

# File đánh dấu dành riêng cho harness
markers = [
    ".harness.lock",
    ".solocode",
]
"""


def _transform_agent_frontmatter(source_text: str, filename: str) -> str:
    """Transform OpenCode/Kilo agent YAML frontmatter to Copilot .agent.md format.

    OpenCode format uses: mode, color, permission (allow/deny per tool)
    Copilot format uses: description, user-invocable, tools (list of allowed tools)
    """
    body_parts = source_text.split("---", 2)
    if len(body_parts) < 3:
        # No valid YAML frontmatter — return as-is with minimal header
        return f'---\ndescription: "Agent: {filename}"\n---\n{source_text.strip()}'

    raw_yaml = body_parts[1]
    body_md = body_parts[2]

    # Parse key fields from OpenCode/Kilo frontmatter
    description = ""
    mode = "subagent"
    permissions: dict[str, str] = {}
    nested_perms: dict[str, dict[str, str]] = {}
    task_perms: dict[str, str] = {}

    for line in raw_yaml.strip().splitlines():
        stripped = line.strip()
        if stripped.startswith("description:"):
            description = stripped.split(":", 1)[1].strip().strip('"')
        elif stripped.startswith("mode:"):
            mode = stripped.split(":", 1)[1].strip()

    # If no description, derive one from filename
    if not description:
        description = " ".join(
            w.capitalize() if i == 0 else w
            for i, w in enumerate(filename.replace("-", " ").split())
        )

    # Parse permission block (OpenCode/Kilo nested structure)
    lines = raw_yaml.strip().splitlines()
    in_permission = False
    current_tool = ""
    in_task = False

    for _i, line in enumerate(lines):
        stripped = line.strip()
        # Detect top-level keys to track scope
        if stripped.startswith("permission:"):
            in_permission = True
            in_task = False
            continue
        if not in_permission:
            continue
        # Detect when we leave the permission block (new top-level key at column 0)
        if not stripped.startswith(" ") and ":" in stripped:
            key = stripped.split(":", 1)[0].strip()
            if key not in (
                "edit", "bash", "read", "grep", "codesearch", "glob",
                "task", "*",
            ) and not stripped.startswith('"') and not stripped.startswith("'"):
                in_permission = False
                continue
        # Handle task sub-block
        if stripped.startswith("task:"):
            in_task = True
            current_tool = ""
            continue
        if in_task:
            if ":" in stripped and not stripped.startswith('"') and not stripped.startswith("'"):
                parts = stripped.split(":", 1)
                task_key = parts[0].strip()
                task_val = parts[1].strip() if len(parts) > 1 else ""
                if task_val:
                    task_perms[task_key] = task_val
                continue
            elif ":" in stripped:
                parts = stripped.split(":", 1)
                task_val = parts[1].strip() if len(parts) > 1 else ""
                if task_val:
                    task_perms[parts[0].strip().strip('"')] = task_val
                continue
            else:
                in_task = False
                continue
        # Handle tool: value (simple case, e.g., "  read: allow")
        if ":" in stripped:
            parts = stripped.split(":", 1)
            key = parts[0].strip()
            val = parts[1].strip() if len(parts) > 1 else ""
            if key in ("edit", "read", "grep", "bash", "glob", "codesearch"):
                if val and val in ("allow", "ask"):
                    nested_perms.setdefault(key, {})["*"] = val
                    permissions[key] = val
                elif not val:
                    current_tool = key
                continue
            # Nested rule under a tool (e.g., '  "*": ask')
            if current_tool:
                cleaned_key = key.strip('"').strip("'")
                if val:
                    nested_perms.setdefault(current_tool, {})[cleaned_key] = val
                continue

    # Map OpenCode permissions to Copilot tool aliases
    tool_map = {
        "edit": "Edit",
        "read": "Read",
        "grep": "Grep",
        "bash": "Bash",
        "glob": "Glob",
    }
    allowed_tools: list[str] = []
    for perm_key in ("read", "edit", "grep", "bash", "glob"):
        if perm_key in nested_perms:
            # Include if any rule allows (or asks) — Copilot doesn't distinguish
            perms = nested_perms[perm_key]
            if any(v in ("allow", "ask") for v in perms.values()) and perm_key in tool_map:
                allowed_tools.append(tool_map[perm_key])
        elif perm_key in permissions and permissions[perm_key] in ("allow", "ask"):
            if perm_key in tool_map:
                allowed_tools.append(tool_map[perm_key])

    # Build Copilot-format frontmatter
    copilot_frontmatter = f'description: "{description}"\n'
    if mode == "primary":
        copilot_frontmatter += "user-invocable: true\n"
    else:
        copilot_frontmatter += "user-invocable: false\n"
    if allowed_tools:
        tools_str = ", ".join(allowed_tools)
        copilot_frontmatter += f"tools: [{tools_str}]\n"
    # Map task permissions to Copilot agents restriction
    if task_perms:
        allowed_agents = [k for k, v in task_perms.items() if v == "allow"]
        if allowed_agents:
            agents_str = ", ".join(allowed_agents)
            copilot_frontmatter += f"agents: [{agents_str}]\n"

    return f"---\n{copilot_frontmatter}---\n{body_md.strip()}\n"


def _copy_copilot_agents_to_github(
    target: Path, dry_run: bool = False
) -> tuple[int, int]:
    """Copy .copilot/agents/*.md → .github/agents/*.agent.md for Copilot discovery.

    Copilot reads custom agents from .github/agents/*.agent.md, not .copilot/agents/.
    Returns (new_count, updated_count).
    """
    copilot_agents_src = ROOT / ".copilot" / "agents"
    github_agents_dst = target / ".github" / "agents"

    if not copilot_agents_src.is_dir():
        return 0, 0

    new_count, updated_count = 0, 0
    github_agents_dst.mkdir(parents=True, exist_ok=True)

    for src_file in sorted(copilot_agents_src.glob("*.md")):
        dst_name = src_file.stem + ".agent.md"
        dst_file = github_agents_dst / dst_name

        if dry_run:
            exists = "[UPD]" if dst_file.exists() else "[NEW]"
            print(f"  [DRY] {exists} .github/agents/{dst_name} (from .copilot/agents/{src_file.name})")
            new_count += 1
            continue

        source_text = src_file.read_text(encoding="utf-8")
        transformed = _transform_agent_frontmatter(source_text, src_file.stem)

        old_text = dst_file.read_text(encoding="utf-8") if dst_file.exists() else ""

        if old_text != transformed:
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            dst_file.write_text(transformed, encoding="utf-8")
            if old_text:
                print(f"  [UPD] .github/agents/{dst_name}")
                updated_count += 1
            else:
                print(f"  [NEW] .github/agents/{dst_name}")
                new_count += 1

    return new_count, updated_count


def _generate_harness_lock(target: Path, dry_run: bool = False) -> None:
    """Generate .harness.lock with current timestamp and version."""
    if dry_run:
        print("  [DRY] Would generate: .harness.lock")
        return

    # Read version from source pyproject.toml
    version = "3.3.0"
    src_pyproject = ROOT / "pyproject.toml"
    if src_pyproject.is_file():
        for line in src_pyproject.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped == 'dynamic = ["version"]':
                # hatch-vcs — use fallback
                continue
            if stripped.startswith("fallback-version"):
                version = stripped.split("=", 1)[1].strip().strip('"')
                break

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    content = HARNESS_LOCK_TEMPLATE.format(version=version, timestamp=timestamp)
    lock_path = target / ".harness.lock"
    lock_path.write_text(content, encoding="utf-8")
    print(f"  [NEW] .harness.lock — generated (v{version})")


# ═══════════════════════════════════════════════════════════════════════
# Core logic
# ═══════════════════════════════════════════════════════════════════════

def should_copy(path: Path) -> bool:
    """Check if a file/dir should be copied (not excluded)."""
    name = path.name
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return False
    if path.is_file() and name in EXCLUDE_FILES:
        return False
    return not (path.is_file() and name.endswith(".pyc"))


def copy_file(src: Path, dst: Path, dry_run: bool, base: Path | None = None) -> str:
    """Copy a single file. Returns status string.

    Args:
        src: Source file to copy.
        dst: Destination path.
        dry_run: If True, only print what would be done.
        base: Base path for display (defaults to dst.parent).
    """
    display = base or dst.parent
    rel = dst.relative_to(display) if display else dst.name

    if dry_run:
        return f"  [DRY] {rel}"

    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        shutil.copy2(src, dst)
        return f"  [UPD] {rel}"
    else:
        shutil.copy2(src, dst)
        return f"  [NEW] {rel}"


def copy_tree(src: Path, dst: Path, dry_run: bool) -> tuple[int, int, list[str]]:
    """Recursively copy a directory tree. Returns (new, updated, skipped)."""
    new, updated, skipped = 0, 0, []

    if not src.is_dir():
        return 0, 0, [f"  [SKIP] {src} — not found"]

    for item in src.rglob("*"):
        if not should_copy(item):
            continue

        rel = item.relative_to(src)
        target = dst / rel

        if item.is_dir():
            if not dry_run:
                target.mkdir(parents=True, exist_ok=True)
        else:
            if dry_run:
                skipped.append(f"  [DRY] {target}")
                new += 1
            elif target.exists():
                shutil.copy2(item, target)
                updated += 1
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
                new += 1

    return new, updated, skipped


def _run_command(cmd: list[str], cwd: Path, label: str, dry_run: bool) -> bool:
    """Run a shell command, return True on success."""
    if dry_run:
        print(f"  [DRY] $ {' '.join(cmd)}")
        return True

    print(f"  [{label}] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [{label}] FAILED (exit {result.returncode})")
        if result.stderr.strip():
            for line in result.stderr.strip().splitlines()[:10]:
                print(f"    {line}")
        return False
    if result.stdout.strip():
        for line in result.stdout.strip().splitlines()[:5]:
            print(f"    {line}")
    print(f"  [{label}] OK")
    return True


# ═══════════════════════════════════════════════════════════════════════
# Scaffold mode — create new project from scratch
# ═══════════════════════════════════════════════════════════════════════

def scaffold(
    target: str,
    *,
    engine: str = "all",
    dry_run: bool = False,
    project_name: str | None = None,
    description: str = "A Solo-Code harness project with AI agent discipline.",
) -> int:
    """Create a brand-new project with full harness scaffolding.

    Steps:
      1. Create target directory (if missing)
      2. Initialize git repository
      3. Copy all harness files (root + engine dirs)
      4. Generate README.md
      5. Run post-scaffold validation
      6. Show next steps
    """
    target_path = Path(target).resolve()
    project_name = project_name or target_path.name

    # ── Step 0: Check target ─────────────────────────────────────
    if target_path.exists() and not target_path.is_dir():
        print(f"[ERROR] Target exists and is not a directory: {target_path}")
        return 1

    exists = target_path.exists()
    mode = "DRY RUN" if dry_run else "LIVE"

    print(f"{'='*60}")
    print(f"  Solo-Code Harness Scaffold ({mode})")
    print(f"{'='*60}")
    print(f"  Project : {project_name}")
    print(f"  Target  : {target_path}")
    print(f"  Engine  : {engine}")
    print()

    # ── Step 1: Create target directory ──────────────────────────
    if not dry_run and not exists:
        target_path.mkdir(parents=True, exist_ok=True)
        print(f"  [DIR] Created: {target_path}")
    elif dry_run and not exists:
        print(f"  [DRY] Would create: {target_path}")

    # ── Step 2: Copy harness files ───────────────────────────────
    if engine == "opencode":
        dirs = DIRS_OPENCODE
    elif engine == "copilot":
        dirs = DIRS_COPILOT
    elif engine == "claude":
        dirs = DIRS_CLAUDE
    else:
        dirs = DIRS_ALL

    total_new, total_upd, total_skip = 0, 0, 0

    print("--- Root Files ---")
    for f in ROOT_FILES:
        src = ROOT / f
        if not src.exists():
            print(f"  [SKIP] {f} — not found (source)")
            total_skip += 1
            continue
        status = copy_file(src, target_path / f, dry_run, base=target_path)
        print(status)
        if "[NEW]" in status or "[DRY]" in status:
            total_new += 1
        elif "[UPD]" in status:
            total_upd += 1

    # Copy .gitignore last so it can't be overwritten by dir copies
    # Already handled in ROOT_FILES

    for d in dirs:
        src = ROOT / d
        name = d.rstrip("/").replace("\\", "/")
        print(f"\n--- {name}/ ---")
        dst = target_path / d
        n, u, skipped = copy_tree(src, dst, dry_run)

        for s in skipped[:5]:
            print(s)
        if len(skipped) > 5:
            print(f"  ... and {len(skipped) - 5} more files")

        total_new += n
        total_upd += u
        total_skip += len(skipped)

        if not dry_run:
            print(f"  Copied: {n} new, {u} updated")

    # ── Step 2.4: Generate .github/agents/ for Copilot ───────────
    if engine in ("all", "copilot"):
        print("\n--- .github/agents/ (Copilot) ---")
        cn, cu = _copy_copilot_agents_to_github(target_path, dry_run)
        total_new += cn
        total_upd += cu

    # ── Step 2.5: Generate .harness.lock ─────────────────────────
    print("\n--- .harness.lock ---")
    _generate_harness_lock(target_path, dry_run)
    total_new += 1

    # ── Step 3: Generate README.md (only if not exists) ──────────
    readme_path = target_path / "README.md"
    if not dry_run and not readme_path.exists():
        readme_content = README_TEMPLATE.format(
            project_name=project_name,
            description=description,
        )
        readme_path.write_text(readme_content, encoding="utf-8")
        print("\n  [NEW] README.md — generated")
        total_new += 1
    elif dry_run and not readme_path.exists():
        print("\n  [DRY] Would generate: README.md")

    # ── Step 4: Create tools/ directory for harness scripts ──────
    # The script itself is already copied via .github/ but we also
    # need deploy.py, generate_harness.py etc. in the new project.
    # Those live inside .github/scripts/ or tools/ — already handled
    # by the dir copies above.

    # ── Step 5: Git init ─────────────────────────────────────────
    git_dir = target_path / ".git"
    if not git_dir.exists():
        ok = _run_command(
            ["git", "init"],
            cwd=target_path,
            label="GIT",
            dry_run=dry_run,
        )
        if ok and not dry_run:
            # Set default branch to main
            _run_command(
                ["git", "checkout", "-b", "main"],
                cwd=target_path,
                label="GIT",
                dry_run=dry_run,
            )

    # ── Step 6: Create initial commit message ────────────────────
    if not dry_run and git_dir.exists():
        # Check if there's anything to commit
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(target_path),
            capture_output=True, text=True,
        )
        if result.stdout.strip():
            _run_command(
                ["git", "add", "."],
                cwd=target_path,
                label="GIT",
                dry_run=False,
            )
            _run_command(
                ["git", "commit", "-m", f"Initial scaffold: Solo-Code Harness ({engine} engine)\n\nCo-Authored-By: Solo-Code <admin@solo-code.com>"],
                cwd=target_path,
                label="GIT",
                dry_run=False,
            )

    # ── Summary ─────────────────────────────────────────────────
    print()
    print("=" * 60)
    if dry_run:
        print(f"  DRY RUN — would scaffold project with {total_new} new files")
    else:
        print(f"  Scaffolded: {total_new} new, {total_upd} updated, {total_skip} skipped")
    print("=" * 60)

    # ── Post-scaffold instructions ───────────────────────────────
    if not dry_run:
        print()
        print("  " + "=" * 56)
        print("  POST-SCAFFOLD SETUP")
        print("  " + "=" * 56)
        print()
        print(f"  cd {target_path}")
        print()
        print("  1. Generate harness artifacts:")
        print("     python tools/generate_harness.py --harness all")
        print()
        print("  2. Validate schemas:")
        print("     python tools/validate_schemas.py")
        print()
        print("  3. Run security scan:")
        print("     python .github/scripts/security_scan.py .")
        print()
        print("  4. Run full checklist:")
        print("     python .github/scripts/checklist.py .")
        print()
        print("  5. Open in your editor:")
        print("     code .")
        print()
        print("  " + "=" * 56)
        print("  Happy Solo-Coding!")
        print("  " + "=" * 56)

    return 0


# ═══════════════════════════════════════════════════════════════════════
# Deploy mode — copy harness to existing project
# ═══════════════════════════════════════════════════════════════════════

def _build_source_manifest(dirs: list[str]) -> set[str]:
    """Build a set of relative file paths (forward-slash) from source harness dirs."""
    manifest: set[str] = set()
    for d in dirs:
        src = ROOT / d
        if not src.is_dir():
            continue
        for item in src.rglob("*"):
            if not should_copy(item):
                continue
            if item.is_file():
                rel = item.relative_to(ROOT).as_posix()
                manifest.add(rel)
    # Add root files (relative to ROOT)
    for f in ROOT_FILES:
        src = ROOT / f
        if src.is_file():
            manifest.add(f.replace("\\", "/"))
    # .harness.lock is always regenerated — never stale
    manifest.add(".harness.lock")
    return manifest


def _cleanup_stale_files(
    target_path: Path,
    dirs: list[str],
    dry_run: bool,
) -> int:
    """Remove files in target harness dirs that are NOT in the source manifest.

    Only cleans inside known harness directories (dirs + root files).
    Returns number of stale files removed (or would-be-removed in dry_run).
    """
    source_manifest = _build_source_manifest(dirs)
    removed = 0

    # Collect target files inside harness dirs
    for d in dirs:
        dst = target_path / d
        if not dst.is_dir():
            continue
        for item in dst.rglob("*"):
            if item.is_file():
                rel = item.relative_to(target_path).as_posix()
                # Skip files intentionally excluded from copy (personal
                # overrides, .pyc, runtime state) — they are never "stale".
                if not should_copy(item):
                    continue
                # Skip generated directories (not in source manifest)
                if rel.startswith(".github/agents/"):
                    continue
                if rel not in source_manifest:
                    if dry_run:
                        print(f"  [STALE] Would remove: {d}/{item.relative_to(dst).as_posix()}")
                    else:
                        item.unlink()
                        print(f"  [STALE] Removed: {d}/{item.relative_to(dst).as_posix()}")
                    removed += 1

    # Check root-level harness files for staleness
    root_harness_files = {
        f for f in ROOT_FILES
        if (ROOT / f).is_file()
    }
    # .harness.lock is always current (regenerated)
    root_harness_files.add(".harness.lock")
    for f_path in target_path.iterdir():
        if not f_path.is_file():
            continue
        name = f_path.name
        # Only check files whose name matches a known harness file pattern
        # or files that live at the root and are harness artifacts
        if name in root_harness_files or name == ".harness.lock":
            continue  # expected
        # Check if it's a harness root file that's no longer in source
        if name.endswith((".md", ".json", ".jsonc", ".toml", ".yaml", ".yml", ".ps1", ".sh", ".js")) and name not in source_manifest and name not in root_harness_files:
            if dry_run:
                print(f"  [STALE] Would remove root file: {name}")
            else:
                f_path.unlink()
                print(f"  [STALE] Removed root file: {name}")
            removed += 1

    return removed


def deploy(target: str, *, engine: str = "all", dry_run: bool = False) -> int:
    """Deploy harness to an existing target directory."""
    target_path = Path(target).resolve()

    if not target_path.exists():
        print(f"[ERROR] Target does not exist: {target_path}")
        return 1

    if not target_path.is_dir():
        print(f"[ERROR] Target is not a directory: {target_path}")
        return 1

    if engine == "opencode":
        dirs = DIRS_OPENCODE
    elif engine == "copilot":
        dirs = DIRS_COPILOT
    elif engine == "claude":
        dirs = DIRS_CLAUDE
    else:
        dirs = DIRS_ALL

    mode = "DRY RUN" if dry_run else "LIVE"
    print(f"=== Solo-Code Harness Deploy ({mode}) ===")
    print(f"  Source : {ROOT}")
    print(f"  Target : {target_path}")
    print(f"  Engine : {engine}")
    print()

    total_new, total_upd, total_skip = 0, 0, 0

    print("--- Root Files ---")
    for f in ROOT_FILES:
        src = ROOT / f
        if not src.exists():
            print(f"  [SKIP] {f} — not found")
            total_skip += 1
            continue
        status = copy_file(src, target_path / f, dry_run, base=target_path)
        print(status)
        if "[NEW]" in status or "[DRY]" in status:
            total_new += 1
        elif "[UPD]" in status:
            total_upd += 1

    for d in dirs:
        src = ROOT / d
        name = d.rstrip("/").replace("\\", "/")
        print(f"\n--- {name}/ ---")
        dst = target_path / d
        n, u, skipped = copy_tree(src, dst, dry_run)

        for s in skipped[:5]:
            print(s)
        if len(skipped) > 5:
            print(f"  ... and {len(skipped) - 5} more files (use --dry-run for full list)")

        total_new += n
        total_upd += u
        total_skip += len(skipped)

        if not dry_run:
            print(f"  Copied: {n} new, {u} updated")

    # ── Step 2.4: Generate .github/agents/ for Copilot ───────────
    if engine in ("all", "copilot"):
        print("\n--- .github/agents/ (Copilot) ---")
        cn, cu = _copy_copilot_agents_to_github(target_path, dry_run)
        total_new += cn
        total_upd += cu

        # Clean up stale .github/agents/ files not in .copilot/agents/
        copilot_agents_src = ROOT / ".copilot" / "agents"
        github_agents_dir = target_path / ".github" / "agents"
        if copilot_agents_src.is_dir() and github_agents_dir.is_dir():
            expected_names = {
                f.stem + ".agent.md" for f in copilot_agents_src.glob("*.md")
            }
            stale_removed = 0
            for existing in sorted(github_agents_dir.glob("*.agent.md")):
                if existing.name not in expected_names:
                    if dry_run:
                        print(f"  [STALE] Would remove: .github/agents/{existing.name}")
                    else:
                        existing.unlink()
                        print(f"  [STALE] Removed: .github/agents/{existing.name}")
                    stale_removed += 1

    # ── Step 2.5: Cleanup stale files ────────────────────────────
    print("\n--- Stale Cleanup ---")
    removed = _cleanup_stale_files(target_path, dirs, dry_run)
    if removed == 0:
        print("  No stale files found.")
    total_removed = removed

    # ── Generate .harness.lock ──────────────────────────────────
    print("\n--- .harness.lock ---")
    _generate_harness_lock(target_path, dry_run)
    total_new += 1

    print()
    print("=" * 60)
    if dry_run:
        print(f"  DRY RUN — would deploy {total_new} files, update {total_upd}, remove {total_removed} stale")
    else:
        print(f"  Deployed: {total_new} new, {total_upd} updated, {total_skip} skipped, {total_removed} stale removed")
    print("=" * 60)

    if not dry_run:
        print()
        print("  Next steps in target project:")
        print(f"    cd {target_path}")
        print("    python tools/generate_harness.py --harness all")
        print("    python tools/validate_schemas.py")
        print("    python .github/scripts/security_scan.py .")

    return 0


# ═══════════════════════════════════════════════════════════════════════
# Interactive mode — ask user what to do
# ═══════════════════════════════════════════════════════════════════════

def interactive() -> int:
    """Run in interactive mode — ask user for details."""
    print("=" * 60)
    print("  Solo-Code Harness — Interactive Setup")
    print("=" * 60)
    print()

    # Ask mode
    while True:
        mode = input("Mode (scaffold/deploy): ").strip().lower()
        if mode in ("scaffold", "deploy"):
            break
        print("  Please enter 'scaffold' or 'deploy'.")

    # Ask target path
    while True:
        target = input("Target path: ").strip()
        if target:
            break
        print("  Path cannot be empty.")

    # Ask engine
    while True:
        engine = input("Engine (all/opencode/copilot/claude) [all]: ").strip().lower()
        if not engine:
            engine = "all"
            break
        if engine in ("all", "opencode", "copilot", "claude"):
            break
        print("  Please enter 'all', 'opencode', 'copilot', or 'claude'.")

    # Ask dry-run
    dry_run_input = input("Dry run? (y/N): ").strip().lower()
    dry_run = dry_run_input in ("y", "yes")

    # Ask project name (only for scaffold)
    project_name = None
    description = "A Solo-Code harness project with AI agent discipline."
    if mode == "scaffold":
        name_input = input(f"Project name [{Path(target).name}]: ").strip()
        if name_input:
            project_name = name_input
        desc_input = input("Description (optional): ").strip()
        if desc_input:
            description = desc_input

    print()

    # Execute
    if mode == "scaffold":
        return scaffold(
            target,
            engine=engine,
            dry_run=dry_run,
            project_name=project_name,
            description=description,
        )
    else:
        return deploy(target, engine=engine, dry_run=dry_run)


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

def _looks_like_path(value: str) -> bool:
    """Heuristic: does the string look like a filesystem path?"""
    # Contains path separators, or is a dot-relative path, or exists on disk
    if "/" in value or "\\" in value or value in (".", ".."):
        return True
    return bool(Path(value).exists())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deploy or scaffold Solo-Code Harness for new/existing projects.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python tools/deploy.py scaffold /path/to/new-project\n"
            "  python tools/deploy.py deploy /path/to/existing-project\n"
            "  python tools/deploy.py /path/to/target         (auto-detect)\n"
            "  python tools/deploy.py                         (interactive)"
        ),
    )
    parser.add_argument(
        "args",
        nargs="*",
        help="[mode] [target] — mode (scaffold|deploy), target (path to project)",
    )
    parser.add_argument(
        "--engine",
        choices=["all", "opencode", "copilot", "claude"],
        default="all",
        help="Which engine harness to deploy (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be copied without making changes",
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="Project name (scaffold mode only)",
    )
    parser.add_argument(
        "--description",
        type=str,
        default="A Solo-Code harness project with AI agent discipline.",
        help="Project description (scaffold mode only)",
    )

    args = parser.parse_args()
    positional = args.args

    # ── Interactive mode (no args) ───────────────────────────────
    if not positional:
        return interactive()

    # ── Parse positional arguments manually ──────────────────────
    # Patterns:
    #   "scaffold" /path/to/target   → mode=scaffold, target=/path/to/target
    #   "deploy"   /path/to/target   → mode=deploy,   target=/path/to/target
    #   /path/to/target              → auto-detect mode
    #   /path/to/target "scaffold"   → target first, mode second (we handle this too)

    mode = None
    target = None

    for pos in positional:
        if pos in ("scaffold", "deploy") and mode is None:
            mode = pos
        elif target is None:
            target = pos
        else:
            print(f"[WARN] Extra argument ignored: {pos}")

    # ── Auto-detect mode if only target provided ─────────────────
    if mode is None and target is not None:
        target_path = Path(target).resolve()
        if target_path.exists():
            print(f"[AUTO] Target exists — deploying to: {target_path}")
            mode = "deploy"
        else:
            print(f"[AUTO] Target does not exist — scaffolding: {target_path}")
            mode = "scaffold"

    if target is None:
        print("[ERROR] Target path is required.")
        return 1

    if mode == "scaffold":
        return scaffold(
            target,
            engine=args.engine,
            dry_run=args.dry_run,
            project_name=args.name,
            description=args.description,
        )
    else:
        return deploy(target, engine=args.engine, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
