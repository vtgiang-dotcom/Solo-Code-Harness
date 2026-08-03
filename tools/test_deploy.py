#!/usr/bin/env python3
"""
Deploy Safety Tests
===================
Regression guards for tools/deploy.py's stale-cleanup logic.

Background: _cleanup_stale_files() used to decide what to delete at a target
project's ROOT by matching file EXTENSIONS (.md/.json/.yml/.ps1/...). Every
config file of a normal JS/TS/Docker project matches that filter, so deploying
the harness into a real project silently deleted package.json, package-lock.json,
tsconfig.json, docker-compose.yml and README.md from disk — breaking the build
with "Module not found: Can't resolve '@/lib/...'" once the tsconfig path
aliases disappeared.

The fix: cleanup may only remove root files the harness itself deployed
(ROOT_FILES + RETIRED_ROOT_FILES + .harness.lock). These tests pin that.

Usage:
    python -m pytest tools/test_deploy.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import deploy  # noqa: E402


def _write(path: Path, text: str = "{}") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# Files a typical target project owns at its root. None of these belong to
# the harness, so none may ever be deleted by a deploy.
PROJECT_ROOT_FILES = [
    "package.json",
    "package-lock.json",
    "tsconfig.json",
    "docker-compose.yml",
    "next.config.mjs",
    "vite.config.ts",
    "README.md",
    "SPEC.md",
    "plan.md",
    "Dockerfile",
    "server.py",
    "pnpm-lock.yaml",
    "biome.json",
    "turbo.json",
    "renovate.json",
    "CHANGELOG.md",
]


def _make_project(tmp_path: Path) -> Path:
    proj = tmp_path / "target"
    for name in PROJECT_ROOT_FILES:
        _write(proj / name)
    _write(proj / "src" / "index.ts", "export {}\n")
    return proj


def test_project_root_files_survive_deploy(tmp_path):
    """The regression: deploy must not delete project-owned root files."""
    proj = _make_project(tmp_path)

    removed = deploy._cleanup_stale_files(proj, deploy.DIRS_ALL, dry_run=False)

    survivors = {p.name for p in proj.iterdir() if p.is_file()}
    missing = [n for n in PROJECT_ROOT_FILES if n not in survivors]
    assert not missing, f"deploy deleted project-owned files: {missing}"
    assert removed == 0, f"nothing was stale, but {removed} file(s) removed"


def test_dry_run_does_not_touch_disk(tmp_path):
    proj = _make_project(tmp_path)
    before = {p.name for p in proj.iterdir() if p.is_file()}

    deploy._cleanup_stale_files(proj, deploy.DIRS_ALL, dry_run=True)

    after = {p.name for p in proj.iterdir() if p.is_file()}
    assert before == after, "dry_run must not modify the filesystem"


def test_retired_harness_file_is_removed(tmp_path):
    """Cleanup must still do its job for files the harness once deployed."""
    proj = _make_project(tmp_path)
    _write(proj / "opencode.json")   # shipped pre-v4.0.0, now retired
    _write(proj / "opencode.ps1")

    removed = deploy._cleanup_stale_files(proj, deploy.DIRS_ALL, dry_run=False)

    assert not (proj / "opencode.json").exists(), "retired harness file not cleaned"
    assert not (proj / "opencode.ps1").exists(), "retired harness file not cleaned"
    assert removed == 2, f"expected 2 removals, got {removed}"
    # ...and the project's own files are still untouched.
    assert (proj / "package.json").exists()
    assert (proj / "tsconfig.json").exists()


def test_current_harness_files_are_kept(tmp_path):
    """Files the harness actively ships must not be flagged stale."""
    proj = _make_project(tmp_path)
    shipped = [f for f in deploy.ROOT_FILES if (deploy.ROOT / f).is_file()]
    assert shipped, "expected some ROOT_FILES to exist in the source repo"
    for name in shipped:
        _write(proj / name)

    deploy._cleanup_stale_files(proj, deploy.DIRS_ALL, dry_run=False)

    for name in shipped:
        assert (proj / name).exists(), f"actively-shipped harness file deleted: {name}"


def test_cleanup_scope_is_a_closed_set(tmp_path):
    """No project-owned name may leak into the harness-owned delete list."""
    owned = deploy.HARNESS_OWNED_ROOT_FILES
    for name in PROJECT_ROOT_FILES:
        assert name not in owned, (
            f"{name!r} is a project-owned file but appears in "
            f"HARNESS_OWNED_ROOT_FILES — deploy would delete it"
        )


def test_retired_files_are_not_also_shipped(tmp_path):
    """A name cannot be both actively shipped and retired."""
    overlap = set(deploy.ROOT_FILES) & deploy.RETIRED_ROOT_FILES
    assert not overlap, f"names are both shipped and retired: {overlap}"


# ─── shared directories (.github / .vscode / tools) ─────────────────────────
#
# Second instance of the same bug class: the per-directory loop deleted
# everything not in the current manifest, but .github/.vscode/tools are
# SHARED with the target project. A deploy would have wiped the project's
# CI workflows, CODEOWNERS, dependabot config, editor settings and dev
# scripts. Only explicitly retired harness files may be removed there.

PROJECT_SHARED_FILES = {
    ".github/workflows/deploy-prod.yml": "name: deploy\n",
    ".github/workflows/ci.yml": "name: project CI\n",
    ".github/CODEOWNERS": "* @team\n",
    ".github/dependabot.yml": "version: 2\n",
    ".github/ISSUE_TEMPLATE/bug.md": "bug\n",
    ".vscode/launch.json": "{}\n",
    ".vscode/settings.json": "{}\n",
    "tools/seed_db.py": "print(1)\n",
    "tools/migrate.sh": "echo hi\n",
}


def _make_shared(tmp_path: Path) -> Path:
    proj = tmp_path / "shared"
    for rel, body in PROJECT_SHARED_FILES.items():
        _write(proj / rel, body)
    return proj


def test_project_files_in_shared_dirs_survive(tmp_path):
    proj = _make_shared(tmp_path)

    removed = deploy._cleanup_stale_files(proj, deploy.DIRS_ALL, dry_run=False)

    for rel, body in PROJECT_SHARED_FILES.items():
        p = proj / rel
        assert p.exists(), f"deploy deleted project file in shared dir: {rel}"
        assert p.read_text(encoding="utf-8") == body, f"content changed: {rel}"
    assert removed == 0, f"nothing was stale, but {removed} file(s) removed"


def test_retired_shared_file_is_removed(tmp_path):
    """Cleanup must still remove harness files that shared dirs once held."""
    proj = _make_shared(tmp_path)
    for rel in deploy.RETIRED_SHARED_FILES:
        _write(proj / rel, "stale harness file\n")

    removed = deploy._cleanup_stale_files(proj, deploy.DIRS_ALL, dry_run=False)

    for rel in deploy.RETIRED_SHARED_FILES:
        assert not (proj / rel).exists(), f"retired harness file not cleaned: {rel}"
    assert removed == len(deploy.RETIRED_SHARED_FILES)
    # Project files in the same directories are untouched.
    for rel in PROJECT_SHARED_FILES:
        assert (proj / rel).exists(), f"collateral damage: {rel}"


def test_retired_shared_files_are_cleanable_despite_exclusion(tmp_path):
    """Regression: should_copy() must not shadow retired-file cleanup.

    Files are usually retired *by being added to EXCLUDE_FILES*, which makes
    should_copy() return False. When the should_copy() skip ran first, those
    files became permanently uncleanable — cleanup silently removed nothing.
    """
    assert deploy.RETIRED_SHARED_FILES, "expected at least one retired shared file"
    for rel in deploy.RETIRED_SHARED_FILES:
        proj = tmp_path / f"case_{Path(rel).name}"
        _write(proj / rel, "x\n")
        removed = deploy._cleanup_stale_files(proj, deploy.DIRS_ALL, dry_run=False)
        assert removed == 1, f"{rel} was not cleaned (removed={removed})"


def test_shared_dirs_are_disjoint_from_exclusive(tmp_path):
    overlap = deploy.SHARED_DIRS & deploy.EXCLUSIVE_HARNESS_DIRS
    assert not overlap, f"a dir cannot be both shared and exclusive: {overlap}"


def test_every_deployed_dir_is_classified(tmp_path):
    """A new DIRS_ALL entry must be declared shared or exclusive.

    Otherwise it silently defaults to full-wipe cleanup — the exact failure
    mode that destroyed project files in .github/ and tools/.
    """
    known = deploy.SHARED_DIRS | deploy.EXCLUSIVE_HARNESS_DIRS
    unclassified = [d for d in deploy.DIRS_ALL if d not in known]
    assert not unclassified, (
        f"unclassified deploy dirs {unclassified} — add each to SHARED_DIRS "
        f"(project also owns files there) or EXCLUSIVE_HARNESS_DIRS"
    )


def test_retired_shared_files_live_in_shared_dirs(tmp_path):
    for rel in deploy.RETIRED_SHARED_FILES:
        top = rel.split("/", 1)[0]
        assert top in deploy.SHARED_DIRS, (
            f"{rel} is listed as a retired SHARED file but {top}/ is not a shared dir"
        )
