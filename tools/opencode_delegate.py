#!/usr/bin/env python3
"""
opencode_delegate.py — CLI-based delegation wrapper for OpenCode workers.

ORCHESTRATION MODEL: Claude Code is ALWAYS the orchestrator.
This script uses `opencode run` to send a single stateless prompt to OpenCode
and parses the JSON events stream. The orchestrator must read and verify every result.

CLI APPROACH (OpenCode run):
  opencode run "prompt" --format json --auto --model provider/model

IMPROVEMENTS OVER Kilo CLI:
  1. Free models — opencode/deepseek-v4-flash-free costs $0
  2. Reasoning tokens — tracks reasoning tokens separately
  3. Cache tracking — separate cache read/write token counts
  4. Multi-provider — commandcode, DeepSeek, OpenAI, Anthropic, OpenRouter, ZenMux
  5. Session export — opencode export <sessionID> for full JSON transcript
  6. Stats command — opencode stats for usage analytics

Usage:
    python tools/opencode_delegate.py "<self-contained prompt>"
    python tools/opencode_delegate.py "<prompt>" --model commandcode/deepseek-v4-pro
    python tools/opencode_delegate.py "<prompt>" --model opencode/deepseek-v4-flash-free
    python tools/opencode_delegate.py "<prompt>" --no-guardrail

Requires OpenCode CLI installed: https://opencode.ai/install
Auth: opencode providers login <url>
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Constants ────────────────────────────────────────────────────────────────

DEFAULT_MODEL = "commandcode/deepseek-v4-pro"
FREE_MODEL = "opencode/deepseek-v4-flash-free"

USAGE_LOG = Path(".solocode/opencode-usage.jsonl")
USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)

GUARDRAIL = """\
STRICT OPERATING CONSTRAINTS (must follow, no exceptions):
1. Modify ONLY the files explicitly named in the task below. Do not touch
   any other file, and do not refactor nearby code that wasn't asked for.
2. Do NOT add new dependencies, new files, or new abstractions unless the
   task explicitly asks for them.
3. Match the existing code style/conventions of the surrounding file
   exactly (naming, formatting, error handling patterns).
4. If the task is ambiguous or underspecified, STOP and report back what
   is missing instead of guessing or inventing scope.
5. Never run destructive commands (git push, --force, rm -rf, DB
   migrations) under any circumstance.
6. End your response with a one-line self-check: "Scope check: touched
   only <file list>; no dependencies added" (or state exactly what
   deviated and why).

"""

# ── Helper Functions ─────────────────────────────────────────────────────────

def _stderr(msg: str) -> None:
    """Print to stderr with [opencode_delegate] prefix."""
    print(f"[opencode_delegate] {msg}", file=sys.stderr)


def find_opencode_binary() -> str | None:
    """Find OpenCode CLI binary. Check PATH first, then common install locations."""
    # Check PATH
    opencode_path = shutil.which("opencode")
    if opencode_path:
        return opencode_path

    # Check ~/.opencode/bin (standard install location)
    home_opencode = Path.home() / ".opencode" / "bin" / "opencode"
    if home_opencode.exists():
        return str(home_opencode)

    # Check Windows user profile
    if sys.platform == "win32":
        win_opencode = Path.home() / ".opencode" / "bin" / "opencode.exe"
        if win_opencode.exists():
            return str(win_opencode)

    return None


def parse_json_events(output: str) -> dict[str, Any]:
    """Parse JSON events stream from opencode run --format json output.

    Returns dict with:
        - text: concatenated text from all text events
        - events: list of all parsed events
        - session_id: session ID from first event
        - tokens: token usage from step_finish event (includes reasoning + cache)
        - cost: cost from step_finish event
        - error: error message if any error event found
    """
    result: dict[str, Any] = {
        "text": "",
        "events": [],
        "session_id": None,
        "tokens": None,
        "cost": None,
        "error": None,
    }

    for line in output.strip().split("\n"):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
            result["events"].append(event)

            # Extract session ID from first event
            if result["session_id"] is None and "sessionID" in event:
                result["session_id"] = event["sessionID"]

            # Concatenate text from text events
            if event.get("type") == "text":
                part = event.get("part", {})
                text = part.get("text", "")
                result["text"] += text

            # Extract tokens/cost from step_finish
            if event.get("type") == "step_finish":
                part = event.get("part", {})
                result["tokens"] = part.get("tokens")
                result["cost"] = part.get("cost")

            # Capture errors
            if event.get("type") == "error":
                error_data = event.get("error", {})
                result["error"] = error_data.get("data", {}).get("message", "Unknown error")

        except json.JSONDecodeError:
            # Skip non-JSON lines (banner, warnings)
            continue

    return result


def run_opencode_cli(
    prompt: str,
    model: str,
    directory: str,
    opencode_binary: str,
    timeout_s: int = 120,
) -> dict[str, Any]:
    """Run opencode CLI, return parsed JSON events."""
    cmd = [
        opencode_binary,
        "run",
        prompt,
        "--model", model,
        "--format", "json",
        "--auto",  # auto-approve non-destructive permissions
    ]

    _stderr(f"Running: opencode run ... --model {model} --format json --auto")

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            check=False,
            cwd=directory,
        )

        if proc.returncode != 0 and not proc.stdout.strip():
            # No JSON output, likely binary error
            _stderr(f"opencode CLI failed with exit code {proc.returncode}")
            if proc.stderr:
                _stderr(f"stderr: {proc.stderr[:500]}")
            return {
                "text": "",
                "events": [],
                "session_id": None,
                "tokens": None,
                "cost": None,
                "error": f"opencode CLI exit code {proc.returncode}",
            }

        # Parse JSON events from stdout
        return parse_json_events(proc.stdout)

    except subprocess.TimeoutExpired:
        _stderr(f"opencode CLI timed out after {timeout_s}s")
        return {
            "text": "",
            "events": [],
            "session_id": None,
            "tokens": None,
            "cost": None,
            "error": f"Timeout after {timeout_s}s",
        }
    except Exception as exc:
        _stderr(f"opencode CLI failed: {exc}")
        return {
            "text": "",
            "events": [],
            "session_id": None,
            "tokens": None,
            "cost": None,
            "error": str(exc),
        }


def log_usage(
    model: str,
    prompt_len: int,
    elapsed: float,
    result: dict[str, Any],
) -> None:
    """Log delegation call to .solocode/opencode-usage.jsonl for auditing."""
    entry: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "prompt_chars": prompt_len,
        "elapsed_s": round(elapsed, 2),
        "session_id": result.get("session_id"),
        "usage": result.get("tokens"),
        "cost": result.get("cost"),
        "error": result.get("error"),
    }
    with USAGE_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


# ── Main ─────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="OpenCode CLI delegation wrapper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Every call is logged to " + str(USAGE_LOG),
    )
    parser.add_argument(
        "prompt",
        help="Self-contained task prompt (inline all needed context)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model in provider/model format (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--directory",
        default=".",
        help="Working directory for opencode CLI (default: current dir)",
    )
    parser.add_argument(
        "--no-guardrail",
        action="store_true",
        help="Skip prepending the strict guardrail preamble",
    )
    parser.add_argument(
        "--opencode-bin",
        help="Path to opencode binary (auto-detected if not provided)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Timeout in seconds (default: 120)",
    )
    parser.add_argument(
        "--free",
        action="store_true",
        help=f"Use free model ({FREE_MODEL})",
    )

    args = parser.parse_args(argv)

    # ── Find OpenCode binary ──
    opencode_binary = args.opencode_bin or find_opencode_binary()
    if not opencode_binary:
        _stderr("OpenCode binary not found. Install from https://opencode.ai/install")
        return 1

    _stderr(f"Using OpenCode binary: {opencode_binary}")

    # ── Override model if --free ──
    model = FREE_MODEL if args.free else args.model

    # ── Prepend guardrail unless disabled ──
    prompt = args.prompt
    if not args.no_guardrail:
        prompt = GUARDRAIL + prompt

    _stderr(f"model={model}")

    # ── Run opencode CLI → parse events → log ──
    start = time.monotonic()
    result = run_opencode_cli(
        prompt=prompt,
        model=model,
        directory=args.directory,
        opencode_binary=opencode_binary,
        timeout_s=args.timeout,
    )
    elapsed = time.monotonic() - start

    log_usage(model, len(prompt), elapsed, result)

    # ── Output ──
    if result.get("error"):
        _stderr(f"Error: {result['error']}")
        return 2

    # Print the concatenated text response
    print(result["text"])

    _stderr(f"session={result.get('session_id')}  elapsed={elapsed:.1f}s")
    if result.get("tokens"):
        tokens = result["tokens"]
        _stderr(
            f"tokens: in={tokens.get('input')} out={tokens.get('output')} "
            f"reasoning={tokens.get('reasoning')} total={tokens.get('total')} "
            f"cache_read={tokens.get('cache', {}).get('read')} "
            f"cache_write={tokens.get('cache', {}).get('write')}"
        )
    if result.get("cost") is not None:
        _stderr(f"cost: ${result['cost']:.6f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
