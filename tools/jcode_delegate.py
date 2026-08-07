#!/usr/bin/env python3
"""
jcode_delegate.py — Token-optimized delegation wrapper for jcode workers.

ORCHESTRATION MODEL (important): Claude Code / Kilo Code is ALWAYS the
orchestrator. This script never runs on its own initiative — it is invoked
by the planner engine for exactly one well-specified subtask at a time and
returns a draft the orchestrator must still read and verify. jcode has no
memory of this conversation between calls; it is a stateless worker, not a
delegate that can be "trusted and forgotten".

DEFAULT MODEL: deepseek/deepseek-v4-pro via CommandCode, always with the
strict guardrail preamble (GUARDRAIL) prepended. Claude Code may explicitly
select an allowlisted FreeModel worker for a task that benefits from a
different model. An earlier version of this wrapper routed
"mechanical" subtasks to the cheaper deepseek-v4-flash tier; in real use
that tier proved unreliable (2026-07-25) — the token saved was repeatedly
lost to re-prompting and orchestrator rework, so the cheap tier was
removed rather than left as a footgun. Cost optimization here now comes
entirely from the flag discipline below (--tool-profile none --no-selfdev,
~65% fewer input tokens), not from model downgrading.

Usage:
    python tools/jcode_delegate.py "<self-contained prompt>"
    python tools/jcode_delegate.py "<prompt>" --model gpt-5.4
    python tools/jcode_delegate.py "<prompt>" --with-tools   # let jcode use its own tools

Every call is logged (model, prompt size, token usage, latency) to
.solocode/jcode-usage.jsonl so the cost/latency payoff is auditable rather
than assumed.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USAGE_LOG = ROOT / ".solocode" / "jcode-usage.jsonl"

MODEL = "deepseek/deepseek-v4-pro"
FREE_MODEL_MODELS = {
    "gpt-5.6-sol",
    "gpt-5.6-terra",
}


# Injected verbatim before every task. deepseek-v4-pro is the only model
# this wrapper uses, but it has a measured tendency to go out of scope
# (touch unrelated files, add dependencies, "helpfully" refactor nearby
# code, invent requirements) unless constraints are stated explicitly and
# right next to the task -- this is the mitigation, not optional
# boilerplate. Never call the model without it.
GUARDRAIL = """\
STRICT OPERATING CONSTRAINTS (must follow, no exceptions):
1. Modify ONLY the files explicitly named in the task below. Do not touch
   any other file, and do not "helpfully" refactor nearby code.
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

TASK:
"""


def build_command(
    prompt: str, *, model: str = MODEL, with_tools: bool, json_out: bool
) -> list[str]:
    profile = "commandcode" if model == MODEL else "freemodel-openai"
    cmd = [
        "jcode", "run", GUARDRAIL + prompt,
        "--provider-profile", profile,
        "--model", model,
        "--quiet",
    ]
    if not with_tools:
        # Cuts measured input tokens by ~65% for tasks that don't need
        # jcode's own bash/read/write tools or repo self-dev detection.
        cmd += ["--tool-profile", "none", "--no-selfdev"]
    if json_out:
        cmd.append("--json")
    return cmd


def _load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _configure_freemodel(model: str, env: dict[str, str]) -> int:
    api_key = env.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = env.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
    if not api_key or not base_url:
        print(
            "FreeModel workers require OPENAI_API_KEY and OPENAI_BASE_URL.",
            file=sys.stderr,
        )
        return 1

    base_url = base_url.rstrip("/")
    for suffix in ("/v1/chat/completions", "/v1/responses", "/v1"):
        if base_url.endswith(suffix):
            base_url = base_url[: -len(suffix)]
            break

    os.environ["JCODE_PROVIDER_FREEMODEL_OPENAI_API_KEY"] = api_key
    config_cmd = [
        "jcode", "provider", "add", "freemodel-openai",
        "--base-url", f"{base_url}/v1",
        "--model", model,
        "--api-key-env", "JCODE_PROVIDER_FREEMODEL_OPENAI_API_KEY",
        "--env-file", "provider-freemodel-openai.env",
        "--auth", "bearer",
        "--overwrite",
        "--quiet",
    ]
    # Fixed argv, no shell. `model` is allowlisted by argparse `choices`, and
    # base_url comes from this repo's own .env -- not from the delegated prompt.
    configured = subprocess.run(  # noqa: S603
        config_cmd, capture_output=True, text=True
    )
    if configured.returncode != 0:
        print(configured.stderr or configured.stdout, file=sys.stderr)
    return configured.returncode


def _log_usage(
    model: str, prompt_len: int, result: dict | None, elapsed: float
) -> None:
    USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "prompt_chars": prompt_len,
        "elapsed_s": round(elapsed, 2),
        "usage": (result or {}).get("usage") if isinstance(result, dict) else None,
    }
    with USAGE_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model", default=MODEL,
        choices=[MODEL, *sorted(FREE_MODEL_MODELS)],
        help=f"Worker model (default: {MODEL})",
    )
    parser.add_argument(
        "prompt", help="Self-contained task prompt (inline all needed context)"
    )
    parser.add_argument(
        "--tier", choices=["simple", "code", "auto"], default=None,
        help="DEPRECATED and ignored. The flash/simple tier was removed "
             "(unreliable in practice); every call now uses "
             f"{MODEL} with the guardrail preamble.",
    )
    parser.add_argument(
        "--with-tools", action="store_true",
        help="Allow jcode's own bash/read/write tools (costs more tokens; "
             "only needed if the subtask genuinely requires them)",
    )
    parser.add_argument(
        "--no-json", action="store_true", help="Stream text instead of --json"
    )
    args = parser.parse_args(argv)

    if args.tier is not None:
        print(
            f"[jcode_delegate] --tier is deprecated and ignored; using {MODEL}.",
            file=sys.stderr,
        )

    if shutil.which("jcode") is None:
        print("jcode binary not found on PATH -- cannot delegate.", file=sys.stderr)
        return 1

    if args.model != MODEL:
        configured = _configure_freemodel(args.model, _load_env_file(ROOT / ".env"))
        if configured != 0:
            return configured

    cmd = build_command(
        args.prompt,
        model=args.model,
        with_tools=args.with_tools,
        json_out=not args.no_json,
    )

    print(f"[jcode_delegate] model={args.model}", file=sys.stderr)

    start = time.monotonic()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.monotonic() - start

    result: dict | None = None
    if not args.no_json and proc.stdout:
        try:
            parsed = json.loads(proc.stdout)
            result = parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            result = None

    _log_usage(args.model, len(args.prompt), result, elapsed)

    if proc.returncode != 0:
        print(proc.stderr or "jcode exited non-zero with no stderr", file=sys.stderr)
        return proc.returncode

    print(proc.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
