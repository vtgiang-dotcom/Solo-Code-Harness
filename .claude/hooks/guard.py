#!/usr/bin/env python3
"""
solocode-guard (Claude Code hook) — PreToolUse safety gate.

Port of .opencode/plugins/solocode-guard.js to a Claude Code PreToolUse hook.
Stdlib-only Python (no jq/bash) for Windows portability.

Wired via .claude/settings.json:
    "hooks": { "PreToolUse": [ { "matcher": "Bash|Edit|Write|MultiEdit",
        "hooks": [ { "type": "command",
            "command": "python .claude/hooks/guard.py" } ] } ] }

Protocol:
  - Reads the tool call JSON from stdin: {tool_name, tool_input, ...}.
  - Bash: blocks destructive commands and leaked secrets in the command string.
  - Edit/Write/MultiEdit: blocks writes to protected config files and blocks
    content containing hardcoded secrets.
  - Blocks by printing a PreToolUse deny decision to stdout AND exiting 2
    (stderr feedback) — both are honored by Claude Code.
  - Allows by exiting 0 with no output (normal permission flow applies).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# ─── Destructive Command Patterns (port of BLOCK_PATTERNS) ──────────────────
BLOCK_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("rm_root", re.compile(r"rm\s+-rf?\s+/(?:\s|$|\*|\"|')")),
    ("rm_home", re.compile(r"rm\s+-rf?\s+~")),
    ("rm_wildcard", re.compile(r"rm\s+-rf?\s+\*")),
    ("rm_no_preserve", re.compile(r"rm\s+--no-preserve-root")),
    ("force_push_main", re.compile(r"git\s+push\s+.*(--force|-f)\s+.*(main|master)")),
    ("git_reset_hard", re.compile(r"git\s+reset\s+--hard")),
    ("drop_table", re.compile(r"DROP\s+(?:TABLE|DATABASE)", re.I)),
    ("truncate_table", re.compile(r"TRUNCATE\s+TABLE", re.I)),
    ("dd_raw", re.compile(r"dd\s+if=")),
    ("mkfs", re.compile(r"mkfs\.")),
    ("shred", re.compile(r"shred\s+")),
    ("dev_write", re.compile(r">\s*/dev/sd[a-z]")),
    ("win_del_force", re.compile(r"del\s+/f\s+/s")),
    ("win_remove_recursive", re.compile(r"Remove-Item\s+.*-Recurse.*-Force")),
    # Anchored to a real format invocation: `format` in command position with a
    # drive letter or /fs: switch. A bare \bformat\s also matched
    # `--output-format json`, so the guard blocked ruff and grep -- and a guard
    # that blocks routine tooling teaches people to work around it.
    ("format_disk", re.compile(r"(?:^|[;&|]\s*)format\s+(?:/\S+\s+)*[a-zA-Z]:", re.I)),
    ("diskpart", re.compile(r"\bdiskpart\b")),
    ("shutdown_system", re.compile(r"(?:shutdown|reboot|halt)\b")),
    ("rm_relative_wildcard", re.compile(r"rm\s+-rf?\s+\./")),
    ("rm_r_wildcard", re.compile(r"rm\s+-r\s+\*")),
    ("rm_r_f_wildcard", re.compile(r"rm\s+-r\s+-f\s+\*")),
    ("git_clean_force", re.compile(r"git\s+clean\s+-f")),
    ("rm_system_dir", re.compile(r"rm\s+-rf?\s+/(?:etc|usr|var|bin|lib(?:64)?|boot|sbin|opt|root|sys|proc|dev)(?:/|\s|$)")),
    ("curl_pipe_shell", re.compile(r"(?:curl|wget)\s+.*\|\s*(?:ba)?sh\b")),
    ("dd_device_write", re.compile(r"dd\s+.*of=/dev/")),
    ("chmod_chown_system", re.compile(r"(?:chmod|chown)\s+-R\s+(?:[^/\s]+\s+)*/(?:etc|usr|var|bin|lib(?:64)?|boot|sbin|opt|root|sys|proc|dev)(?:/|\s|$)")),
    ("rm_temp_linux", re.compile(r"rm\s+-rf?\s+/tmp/")),
    ("rm_temp_win", re.compile(r"rm\s+-rf?\s+\$?(?:env:)?TEMP\b", re.I)),
    ("del_temp_win", re.compile(r"del\s+(?:/f\s+)?/[qs]\s+\$?(?:env:)?TEMP\b", re.I)),
    ("win_rd_recursive", re.compile(r"(?:rd|rmdir)\s+(?:.*\s)?/s\b", re.I)),
    ("win_del_any", re.compile(r"del\s+(?:.*\s)?/[qsf]\b", re.I)),
    ("win_format_volume", re.compile(r"\bFormat-Volume\b")),
    ("win_stop_computer", re.compile(r"\bStop-Computer\b")),
    ("win_restart_computer", re.compile(r"\bRestart-Computer\b")),
]

# ─── Secret Detection Patterns (port of SECRET_PATTERNS) ────────────────────
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("aws_access_key", re.compile(r"(?:AKIA|ASIA)[A-Z0-9]{16}")),
    ("aws_secret_key", re.compile(r"(?:aws|amazon).{0,20}(?:secret|key|token).{0,10}[:=]\s*[\"'][A-Za-z0-9/+=]{20,}", re.I)),
    ("generic_api_key", re.compile(r"(?:api[_-]?key|apikey|secret|password)\s*[:=]\s*[\"'][^\"']{8,}[\"']", re.I)),
    ("private_key_pem", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
    ("jwt_token", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("github_token", re.compile(r"(?:gh[pousr]_|github[_-]?pat[_-]?|github[_-]?token[_-]?)[A-Za-z0-9_]{20,}", re.I)),
    ("google_api_key", re.compile(r"AIza[0-9A-Za-z_-]{35}")),
    ("slack_token", re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}")),
    ("stripe_key", re.compile(r"(?:sk|pk)_(?:test|live)_[0-9a-zA-Z]{24,}")),
    ("mongodb_uri", re.compile(r"mongodb(?:\+srv)?://[^:]+:[^@]+@")),
    ("postgres_uri", re.compile(r"postgres(?:ql)?://[^:]+:[^@]+@")),
    ("redis_uri", re.compile(r"redis://[^:]+:[^@]+@")),
    ("hardcoded_token", re.compile(r"(?:token|bearer)\s*[:=]\s*[\"'][A-Za-z0-9._\-+/=]{20,}[\"']", re.I)),
    ("discord_webhook", re.compile(r"https://discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_-]+", re.I)),
    ("basic_auth", re.compile(r"https?://[^:]+:[^@]+@")),
    # Prefixed-token formats. `generic_api_key` only fires on a QUOTED value,
    # so bare `KEY=sk-ant-...` shell/env forms passed straight through -- this
    # project's own Anthropic key format included. Length floors sit above
    # doc-placeholder length so README examples do not trip the gate.
    # Pinned by tools/test_secret_patterns.py.
    ("anthropic_key", re.compile(r"sk-ant-[A-Za-z0-9\-_]{24,}")),
    ("openai_project_key", re.compile(r"sk-proj-[A-Za-z0-9\-_]{20,}")),
    ("npm_token", re.compile(r"npm_[A-Za-z0-9]{36}")),
    ("gitlab_pat", re.compile(r"glpat-[A-Za-z0-9\-_]{20,}")),
    ("digitalocean_token", re.compile(r"dop_v1_[A-Za-z0-9]{64}")),
    # Authorization header form: no quotes, no "=", so `hardcoded_token` missed it.
    ("bearer_header", re.compile(r"Bearer\s+[A-Za-z0-9._\-+/=]{20,}")),
]

# ─── Protected Config Files (port of PROTECTED_FILES) ───────────────────────
PROTECTED_FILES: frozenset[str] = frozenset({
    ".eslintrc", ".eslintrc.js", ".eslintrc.cjs", ".eslintrc.json",
    ".eslintrc.yml", ".eslintrc.yaml",
    "eslint.config.js", "eslint.config.mjs", "eslint.config.cjs",
    "eslint.config.ts", "eslint.config.mts", "eslint.config.cts",
    ".prettierrc", ".prettierrc.js", ".prettierrc.cjs", ".prettierrc.json",
    ".prettierrc.yml", ".prettierrc.yaml",
    "prettier.config.js", "prettier.config.cjs", "prettier.config.mjs",
    "biome.json", "biome.jsonc",
    ".ruff.toml", "ruff.toml",
    ".shellcheckrc",
    ".stylelintrc", ".stylelintrc.json", ".stylelintrc.yml",
    ".markdownlint.json", ".markdownlint.yaml", ".markdownlintrc",
    ".flake8", ".pylintrc", "tox.ini",
    ".golangci.yml", ".golangci.yaml", ".golangci.json",
    ".editorconfig",
})


def normalize_command(command: str) -> str:
    """Strip sudo/env/bash -c wrappers + collapse whitespace to defeat bypasses."""
    if not command or not isinstance(command, str):
        return ""
    cmd = re.sub(r"\s+", " ", command).strip()
    while True:
        prev = cmd
        cmd = re.sub(r"^sudo\s+", "", cmd)
        cmd = re.sub(r"^env(\s+\w+=[^\s]*)+\s+", "", cmd)
        cmd = re.sub(r"^(?:bash|sh)\s+-c\s+", "", cmd)
        cmd = re.sub(r"^(['\"])(.*)\1$", r"\2", cmd)
        if cmd == prev:
            break
    cmd = re.sub(r"^/?(?:[\w.-]+/)+([\w.-]+)", r"\1", cmd)
    return cmd


def find_destructive(command: str) -> str | None:
    for raw in (command, normalize_command(command)):
        if not raw:
            continue
        for name, pattern in BLOCK_PATTERNS:
            if pattern.search(raw):
                return name
    return None


def find_secret(text: str) -> str | None:
    if not text:
        return None
    for name, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            return name
    return None


# ─── Skill risk declaration ─────────────────────────────────────────────────
#
# A skill that TELLS the agent to run a side-effecting command (deploy, push,
# migrate) must declare `risk: side-effecting` in its frontmatter. The point is
# not the label -- it is that adding such an instruction becomes a deliberate,
# visible act instead of a line that slips into a skill silently.
#
# Only fires on imperative instructions ("Run the migration", "Deploy the ...")
# so a skill may still freely NAME a command: permission-guard documents
# `rm -rf` precisely because it blocks it, and must not be forced to declare
# itself side-effecting for doing so.

SKILL_RISK_VALUES = {"none", "side-effecting"}

_SIDE_EFFECT_INSTRUCTION = re.compile(
    r"^\s*(?:[-*]|\d+\.)?\s*(?:Run|Execute|Push|Deploy|Apply|Publish|Release)\b"
    r"[^\n]*?(git\s+push|deploy|migrat|reset\s+--hard|--force)",
    re.I | re.M,
)


def parse_frontmatter_value(content: str, key: str) -> str | None:
    """Read one top-level scalar from a `---`-delimited frontmatter block."""
    if not content.startswith("---"):
        return None
    end = content.find("\n---", 3)
    if end == -1:
        return None
    for line in content[3:end].splitlines():
        m = re.match(rf"^{re.escape(key)}\s*:\s*(.*)$", line.strip())
        if m:
            return m.group(1).strip().strip("\"'")
    return None


def check_skill_risk(file_path: str, content: str, *, is_full_content: bool) -> str | None:
    """Return a denial reason if a SKILL.md's risk declaration is wrong.

    Content-based, not path-based: the check reads what the skill instructs,
    so it cannot be bypassed by writing the file somewhere else first.

    A partial Edit supplies only the replacement fragment, which carries no
    frontmatter -- reading `risk:` from it would report "not declared" for
    every skill, including correctly-declared ones. So for fragments the
    declaration is read from the file on disk instead.
    """
    if os.path.basename(file_path) != "SKILL.md" or not content:
        return None

    declared_source = content
    if not is_full_content:
        try:
            with open(file_path, encoding="utf-8") as fh:
                declared_source = fh.read()
        except OSError:
            # New file via Edit, or unreadable: no frontmatter to judge
            # against, so stay silent rather than block on a guess.
            return None

    declared = parse_frontmatter_value(declared_source, "risk")
    if declared is not None and declared not in SKILL_RISK_VALUES:
        return (f"SKILL.md declares unknown risk '{declared}'. "
                f"Use one of: {', '.join(sorted(SKILL_RISK_VALUES))}.")

    hit = _SIDE_EFFECT_INSTRUCTION.search(content)
    if hit and declared != "side-effecting":
        return (f"SKILL.md instructs a side-effecting action "
                f"({hit.group(0).strip()[:60]!r}) but does not declare "
                f"'risk: side-effecting' in its frontmatter. Add it, or "
                f"reword so the skill describes rather than instructs.")
    return None


def deny(reason: str) -> None:
    """Emit a Claude PreToolUse deny decision and exit non-zero."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    print(f"[solocode-guard] BLOCKED: {reason}", file=sys.stderr)
    sys.exit(2)


# ─── Executor Mode (orchestrator/executor split) ────────────────────────────
# When enabled, the orchestrator (Claude) may not write files directly: code
# changes must be routed to a worker engine (jcode/DeepSeek, gpt-5.6-sol) via
# tools/jcode_delegate.py. Claude keeps planning, reviewing and verifying.
#
# State lives in .solocode/executor-mode (gitignored, per-machine):
#   file absent            -> ENABLED  (default-on, by design)
#   file contains off|0|disabled|false -> disabled
#   any other content      -> ENABLED
#
# SCOPE, STATED HONESTLY: this gates Edit/Write/MultiEdit only. Bash is
# deliberately NOT gated, so `python -c`, heredocs, `sed -i` and `>` still
# write files. This is a speed bump plus an audit trail, not a sandbox --
# chosen over a stricter gate because Bash-write blocking is an unwinnable
# arms race that also breaks legitimate verification scripts.
EXECUTOR_MODE_OFF_VALUES: frozenset[str] = frozenset({
    "off", "0", "disabled", "false", "no",
})

# Paths the orchestrator must still write for delegation itself to work.
# Kept deliberately short: every entry is a hole in the gate.
EXECUTOR_MODE_ALLOWED_PREFIXES: tuple[str, ...] = (
    # Gemini/Antigravity handoff briefs -- writing the plan IS the delegation.
    ".gemini/antigravity/handoff/inbox/",
    # The toggle itself, so the mode can be turned off without hand-editing.
    ".solocode/executor-mode",
)


def project_root() -> Path:
    """Repo root: CLAUDE_PROJECT_DIR if set, else this hook's grandparent."""
    env_root = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parent.parent.parent


def executor_mode_enabled(root: Path | None = None) -> bool:
    """True when the orchestrator must delegate writes. Default: True."""
    root = root or project_root()
    state_file = root / ".solocode" / "executor-mode"
    try:
        raw = state_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return True  # Absent or unreadable -> default-on.
    return raw.strip().split("#", 1)[0].strip().lower() not in EXECUTOR_MODE_OFF_VALUES


def executor_mode_exempt(file_path: str, root: Path | None = None) -> bool:
    """True if this path is delegation plumbing that stays writable."""
    if not file_path:
        return False
    root = root or project_root()
    path = Path(file_path)
    try:
        rel = (path if path.is_absolute() else root / path).resolve()
        rel_str = rel.relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        # Outside the repo (or unresolvable): not delegation plumbing.
        rel_str = path.as_posix().lstrip("./")
    return rel_str.startswith(EXECUTOR_MODE_ALLOWED_PREFIXES)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # No parseable input — do not block.

    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}

    if tool == "Bash":
        command = tool_input.get("command", "") or ""
        hit = find_destructive(command)
        if hit:
            deny(f"destructive command pattern '{hit}' detected. "
                 f"Run manually if you are certain this is safe.")
        secret = find_secret(command)
        if secret:
            deny(f"possible secret '{secret}' in command. Use environment variables instead.")
        return 0

    if tool in ("Edit", "Write", "MultiEdit"):
        file_path = tool_input.get("file_path", "") or ""
        basename = os.path.basename(file_path)
        if basename in PROTECTED_FILES:
            deny(f"'{basename}' is a protected config file. Confirm before editing linter/formatter config.")
        # Scan proposed content for secrets.
        full_content = tool_input.get("content", "") or ""
        content = full_content or tool_input.get("new_string", "") or ""
        fragments = tool_input.get("edits", []) or []
        for edit in fragments:
            content += "\n" + (edit.get("new_string", "") or "")
        secret = find_secret(content)
        if secret:
            deny(f"possible secret '{secret}' in file content. Use environment variables instead.")
        risk_issue = check_skill_risk(
            file_path, content,
            is_full_content=bool(full_content) and not fragments,
        )
        if risk_issue:
            deny(risk_issue)
        # Executor mode last: the security denials above carry more specific,
        # more urgent messages, so they should win when both would fire.
        if executor_mode_enabled() and not executor_mode_exempt(file_path):
            deny(
                f"executor mode is ON -- the orchestrator does not write files "
                f"directly. Route this change to a worker:\n"
                f"  python tools/jcode_delegate.py \"<self-contained task naming "
                f"{file_path}>\" --with-tools\n"
                f"Then verify the result yourself (read the file back, run the "
                f"gates) before accepting it. Note: workers can misreport which "
                f"path they wrote -- confirm with git status.\n"
                f"To disable: echo off > .solocode/executor-mode"
            )
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
