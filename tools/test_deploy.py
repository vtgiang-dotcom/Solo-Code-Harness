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
