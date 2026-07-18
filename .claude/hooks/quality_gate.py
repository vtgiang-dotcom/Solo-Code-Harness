#!/usr/bin/env python3
"""
quality_gate (Claude Code hook) — PostToolUse formatter/linter check.

Python port of .kilo/hooks/post-tool-use/quality-gate.js. Stdlib-only for
Windows/macOS/Linux portability (no bash/jq/node required).

Wired via .claude/settings.json:
    "PostToolUse": [ { "matcher": "Edit|Write|MultiEdit",
        "hooks": [ { "type": "command",
            "command": "python .claude/hooks/quality_gate.py" } ] } ]

Behavior:
  - Reads the PostToolUse JSON from stdin: {tool_input:{file_path}, ...}.
  - Runs a NON-BLOCKING format check on the edited file, matched by extension:
      .py                                   -> ruff format --check
      .ts/.tsx/.js/.jsx/.json/.md/.css/...  -> prettier or biome (if configured)
      .go                                   -> gofmt -l
  - On check failure, prints a fix hint to stderr; ALWAYS exits 0 so the edit
    is never blocked (advisory only, mirrors the Kilo hook).
  - Opt out entirely with QUALITY_GATE_DISABLE=1.
  - Missing tools / parse errors / any exception -> silent exit 0.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PRETTIER_EXTS = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".json", ".jsonc", ".md", ".mdx", ".css", ".scss", ".html", ".yaml", ".yml",
}
_ROOT_MARKERS = (
    "package.json", "pyproject.toml", "go.mod", "Cargo.toml",
    "biome.json", "biome.jsonc", ".prettierrc", ".git",
)


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str] | None:
    """Run a command, return CompletedProcess or None if the tool is missing."""
    try:
        return subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def _find_project_root(start: Path) -> Path:
    cur = start.resolve()
    for parent in (cur, *cur.parents):
        if any((parent / m).exists() for m in _ROOT_MARKERS):
            return parent
    return Path.cwd()


def _detect_js_formatter(root: Path) -> str | None:
    if (root / "biome.json").exists() or (root / "biome.jsonc").exists():
        return "biome"
    for name in (".prettierrc", ".prettierrc.json", ".prettierrc.js",
                 ".prettierrc.yml", ".prettierrc.yaml", "prettier.config.js"):
        if (root / name).exists():
            return "prettier"
    pkg = root / "package.json"
    if pkg.exists():
        try:
            if "prettier" in json.loads(pkg.read_text(encoding="utf-8")):
                return "prettier"
        except (ValueError, OSError):
            pass
    return None


def _warn(msg: str) -> None:
    sys.stderr.write(f"[QualityGate] {msg}\n")


def check(file_path: str) -> None:
    if not file_path:
        return
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        return

    ext = path.suffix.lower()
    root = _find_project_root(path.parent)

    if ext == ".py":
        res = _run(["ruff", "format", "--check", str(path)], cwd=root)
        if res is not None and res.returncode != 0:
            _warn(f"Ruff format check failed for {path.name}. Run: ruff format \"{path}\"")
        return

    if ext in PRETTIER_EXTS:
        formatter = _detect_js_formatter(root)
        if formatter == "prettier":
            res = _run(["npx", "prettier", "--check", str(path)], cwd=root)
            if res is not None and res.returncode != 0:
                _warn(f"Prettier check failed for {path.name}. Run: npx prettier --write \"{path}\"")
        elif formatter == "biome":
            res = _run(["npx", "@biomejs/biome", "check", str(path)], cwd=root)
            if res is not None and res.returncode != 0:
                _warn(f"Biome check failed for {path.name}")
        return

    if ext == ".go":
        res = _run(["gofmt", "-l", str(path)], cwd=root)
        if res is not None and res.stdout.strip():
            _warn(f"gofmt check failed for {path.name}. Run: gofmt -w \"{path}\"")
        return


def main() -> int:
    if os.environ.get("QUALITY_GATE_DISABLE", "").lower() in ("1", "true"):
        return 0
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    try:
        tool_input = payload.get("tool_input", {}) or {}
        check(tool_input.get("file_path", "") or "")
    except Exception:  # noqa: BLE001 — advisory hook must never crash the tool call
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
