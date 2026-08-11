#!/usr/bin/env python3
"""
kilo_cli_delegate.py — CLI-based delegation wrapper for Kilo workers.

ORCHESTRATION MODEL: Claude Code / Kilo Code is ALWAYS the orchestrator.
This script uses `kilo run --attach` to send a single stateless prompt to a
running Kilo server and parses the JSON events stream. The orchestrator must
read and verify every result.

CLI APPROACH (Kilo run --attach):
  kilo run "prompt" --attach http://server --format json --auto --model provider/model

IMPROVEMENTS OVER jcode (subprocess pattern):
  1. Stable API — JSON events stream with typed schemas vs parsing stdout
  2. Structured JSON — every event has type, timestamp, sessionID, structured data
  3. Observable state — events include step_start, text, tool_use, step_finish
  4. Session tracking — sessionID in every event for debugging
  5. Proper errors — JSON error events with type/message/ref vs exit-code guessing

IMPROVEMENTS OVER kilo_delegate.py (HTTP API):
  6. Works immediately — no debugging HTTP payload structure
  7. Proven stable — kilo run --attach is the official CLI interface
  8. Same benefits — both use same underlying Kilo server

Usage:
    python tools/kilo_cli_delegate.py "<self-contained prompt>"
    python tools/kilo_cli_delegate.py "<prompt>" --model commandcode/deepseek/deepseek-v4-pro
    python tools/kilo_cli_delegate.py "<prompt>" --no-guardrail

Requires Kilo server running: kilo serve --port 14096
Or will auto-find Kilo binary and use --attach to default server.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Constants ────────────────────────────────────────────────────────────────

DEFAULT_SERVER = "http://127.0.0.1:14096"
DEFAULT_MODEL = "commandcode/deepseek/deepseek-v4-pro"

USAGE_LOG = Path(".solocode/kilo-usage.jsonl")
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
    """Print to stderr with [kilo_cli_delegate] prefix."""
    print(f"[kilo_cli_delegate] {msg}", file=sys.stderr)


def find_kilo_binary() -> str | None:
    """Find Kilo CLI binary. Check PATH first, then common install locations."""
    # Check PATH
    kilo_path = shutil.which("kilo")
    if kilo_path:
        return kilo_path

    # Check Antigravity IDE extensions (Windows)
    antigravity_base = Path.home() / ".antigravity-ide" / "extensions"
    if antigravity_base.exists():
        # Find latest version
        kilo_exts = list(antigravity_base.glob("kilocode.kilo-code-*/bin/kilo.exe"))
        if kilo_exts:
            # Sort by version, take latest
            latest = sorted(kilo_exts, reverse=True)[0]
            return str(latest)

    # Check ~/.local/share/kilo (Linux/Mac)
    local_kilo = Path.home() / ".local" / "share" / "kilo" / "bin" / "kilo"
    if local_kilo.exists():
        return str(local_kilo)

    return None


def parse_json_events(output: str) -> dict[str, Any]:
    """Parse JSON events stream from kilo run --format json output.

    Returns dict with:
        - text: concatenated text from all text events
        - events: list of all parsed events
        - session_id: session ID from first event
        - tokens: token usage from step_finish event
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
                result["error"] = event.get("part", {}).get("message", "Unknown error")

        except json.JSONDecodeError:
            # Skip non-JSON lines (banner, warnings)
            continue

    return result


def run_kilo_cli(
    prompt: str,
    model: str,
    server_url: str,
    directory: str,
    kilo_binary: str,
    timeout_s: int = 120,
) -> dict[str, Any]:
    """Run kilo CLI with --attach to server, return parsed JSON events."""
    cmd = [
        kilo_binary,
        "run",
        prompt,
        "--model", model,
        "--attach", server_url,
        "--format", "json",
        "--auto",  # auto-approve non-destructive permissions
        "--dir", directory,
    ]

    _stderr(f"Running: {' '.join(cmd[:3])} ... --model {model} --attach {server_url}")

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )

        if proc.returncode != 0 and not proc.stdout.strip():
            # No JSON output, likely binary error
            _stderr(f"kilo CLI failed with exit code {proc.returncode}")
            if proc.stderr:
                _stderr(f"stderr: {proc.stderr[:500]}")
            return {
                "text": "",
                "events": [],
                "session_id": None,
                "tokens": None,
                "cost": None,
                "error": f"kilo CLI exit code {proc.returncode}",
            }

        # Parse JSON events from stdout
        return parse_json_events(proc.stdout)

    except subprocess.TimeoutExpired:
        _stderr(f"kilo CLI timed out after {timeout_s}s")
        return {
            "text": "",
            "events": [],
            "session_id": None,
            "tokens": None,
            "cost": None,
            "error": f"Timeout after {timeout_s}s",
        }
    except Exception as exc:
        _stderr(f"kilo CLI failed: {exc}")
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
    """Log delegation call to .solocode/kilo-usage.jsonl for auditing."""
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
        description="Kilo CLI delegation wrapper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Every call is logged to " + str(USAGE_LOG),
    )
    parser.add_argument(
        "prompt",
        help="Self-contained task prompt (inline all needed context)",
    )
    parser.add_argument(
        "--server",
        default=DEFAULT_SERVER,
        help=f"Kilo server URL for --attach (default: {DEFAULT_SERVER})",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model in provider/model format (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--directory",
        default=".",
        help="Working directory for kilo CLI (default: current dir)",
    )
    parser.add_argument(
        "--no-guardrail",
        action="store_true",
        help="Skip prepending the strict guardrail preamble",
    )
    parser.add_argument(
        "--no-json",
        action="store_true",
        help="Disable JSON format request (use default text)",
    )
    parser.add_argument(
        "--kilo-bin",
        help="Path to kilo binary (auto-detected if not provided)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Timeout in seconds (default: 120)",
    )

    args = parser.parse_args(argv)

    # ── Find Kilo binary ──
    kilo_binary = args.kilo_bin or find_kilo_binary()
    if not kilo_binary:
        _stderr("Kilo binary not found. Install Kilo CLI or specify --kilo-bin")
        return 1

    _stderr(f"Using Kilo binary: {kilo_binary}")

    # ── Prepend guardrail unless disabled ──
    prompt = args.prompt
    if not args.no_guardrail:
        prompt = GUARDRAIL + prompt

    _stderr(f"server={args.server}  model={args.model}")

    # ── Run kilo CLI → parse events → log ──
    start = time.monotonic()
    result = run_kilo_cli(
        prompt=prompt,
        model=args.model,
        server_url=args.server,
        directory=args.directory,
        kilo_binary=kilo_binary,
        timeout_s=args.timeout,
    )
    elapsed = time.monotonic() - start

    log_usage(args.model, len(prompt), elapsed, result)

    # ── Output ──
    if result.get("error"):
        _stderr(f"Error: {result['error']}")
        return 2

    # Print the concatenated text response
    print(result["text"])

    _stderr(f"session={result.get('session_id')}  elapsed={elapsed:.1f}s")
    if result.get("tokens"):
        tokens = result["tokens"]
        _stderr(f"tokens: in={tokens.get('input')} out={tokens.get('output')} total={tokens.get('total')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
