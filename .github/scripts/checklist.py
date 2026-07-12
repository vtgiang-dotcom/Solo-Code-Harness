#!/usr/bin/env python3
"""
Master Checklist Runner
========================
Orchestrates validation checks in priority order.

Usage:
    python .github/scripts/checklist.py .                    # Core checks
    python .github/scripts/checklist.py . --url <URL>        # Include performance

Priority:
    P0: Security Scan | P1: Lint & Type | P2: Tests | P3: UX | P4: SEO | P5: Perf
"""

import argparse
import subprocess
import sys
from pathlib import Path


class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


# Detect if we need to fall back to ASCII symbols
# (e.g. on Windows with non-UTF-8 encoding)
try:
    "✓".encode(sys.stdout.encoding or "utf-8")
    SYM_OK = "✓"
    SYM_BAD = "✗"
    SYM_WARN = "~"
except UnicodeEncodeError:
    SYM_OK = "PASS"
    SYM_BAD = "FAIL"
    SYM_WARN = "SKIP"


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.ENDC}\n")


def print_step(text: str):
    print(f"{Colors.BOLD}{Colors.BLUE}[ ] {text}{Colors.ENDC}")


def print_success(text: str):
    print(f"{Colors.GREEN}[{SYM_OK}] {text}{Colors.ENDC}")


def print_warning(text: str):
    print(f"{Colors.YELLOW}[{SYM_WARN}] {text}{Colors.ENDC}")


def print_error(text: str):
    print(f"{Colors.RED}[{SYM_BAD}] {text}{Colors.ENDC}")


def run_check(name: str, command: list[str], timeout: int = 120) -> dict:
    """Run a validation check and capture results."""
    print_step(f"Running: {name}")
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=timeout,
        )
        passed = result.returncode == 0
        if passed:
            print_success(f"{name}: PASSED")
        else:
            print_error(f"{name}: FAILED")
            if result.stderr:
                print(f"  {result.stderr[:300]}")
        return {
            "name": name,
            "passed": passed,
            "output": result.stdout,
            "skipped": False,
        }
    except subprocess.TimeoutExpired:
        print_error(f"{name}: TIMEOUT")
        return {"name": name, "passed": False, "output": "", "skipped": False}
    except FileNotFoundError:
        print_warning(f"{name}: Tool not installed, skipping")
        return {"name": name, "passed": True, "output": "", "skipped": True}


def print_summary(results: list[dict]) -> bool:
    """Print final summary report."""
    print_header("CHECKLIST SUMMARY")
    passed = sum(1 for r in results if r["passed"] and not r.get("skipped"))
    failed = sum(1 for r in results if not r["passed"] and not r.get("skipped"))
    skipped = sum(1 for r in results if r.get("skipped"))

    print(
        f"Total: {len(results)} "
        f"| {Colors.GREEN}Passed: {passed}{Colors.ENDC} "
        f"| {Colors.RED}Failed: {failed}{Colors.ENDC} "
        f"| {Colors.YELLOW}Skipped: {skipped}{Colors.ENDC}\n"
    )

    for r in results:
        icon = (
            f"{Colors.YELLOW}{SYM_WARN}{Colors.ENDC}"
            if r.get("skipped")
            else (
                f"{Colors.GREEN}{SYM_OK}{Colors.ENDC}"
                if r["passed"]
                else f"{Colors.RED}{SYM_BAD}{Colors.ENDC}"
            )
        )
        print(f"  {icon} {r['name']}")

    if failed > 0:
        print_error(f"\n{failed} check(s) FAILED — fix before proceeding")
        return False
    print_success("\nAll checks PASSED")
    return True


def main():
    parser = argparse.ArgumentParser(description="Master validation checklist")
    parser.add_argument("project", help="Project path to validate")
    parser.add_argument("--url", help="URL for performance checks")
    args = parser.parse_args()

    project_path = Path(args.project).resolve()
    if not project_path.exists():
        print_error(f"Project path does not exist: {project_path}")
        sys.exit(1)

    print_header("SOLO-CODE CHECKLIST")
    print(f"Project: {project_path}")

    results = []

    # P0: Security scan (scan for hardcoded secrets, exclude vendor dirs)
    print_header("P0: SECURITY")
    scanner = project_path / ".github/scripts/security_scan.py"
    if scanner.exists():
        results.append(
            run_check(
                "Secret Scan",
                [sys.executable, str(scanner), str(project_path)],
                timeout=120,
            )
        )
    else:
        print_warning("security_scan.py not found, skipping secret scan")

    # P1: Lint & Type Check
    print_header("P1: CODE QUALITY")
    results.append(
        run_check(
            "Ruff Linter", ["ruff", "check", str(project_path)], timeout=120
        )
    )

    npm = project_path / "package.json"
    if npm.exists():
        results.append(
            run_check(
                "ESLint", ["npx", "eslint", ".", "--max-warnings", "0"], timeout=120
            )
        )
    else:
        print_warning("No package.json found, skipping ESLint")

    # P2: Tests
    print_header("P2: TESTS")

    # Boundary Audit — ensure no project code leaked into harness dirs
    boundary_auditor = project_path / ".github" / "scripts" / "boundary_audit.py"
    if boundary_auditor.exists():
        results.append(
            run_check(
                "Boundary Audit",
                [sys.executable, str(boundary_auditor), str(project_path)],
                timeout=60,
            )
        )
    else:
        print_warning("boundary_audit.py not found, skipping Boundary Audit")

    # Harness eval
    eval_script = project_path / ".github" / "scripts" / "eval_harness.py"
    if eval_script.exists():
        results.append(
            run_check(
                "Harness Eval",
                [sys.executable, str(eval_script), str(project_path)],
                timeout=120,
            )
        )
    else:
        print_warning("eval_harness.py not found, skipping Harness Eval")

    # Guard plugin tests (OpenCode)
    guard_test = project_path / ".opencode" / "tests" / "test-guard.mjs"
    if guard_test.exists():
        results.append(
            run_check(
                "Guard Tests", ["node", str(guard_test)], timeout=120
            )
        )
    else:
        print_warning("test-guard.mjs not found, skipping Guard Tests")

    if npm.exists():
        results.append(
            run_check("Tests", ["npm", "test", "--", "--passWithNoTests"], timeout=300)
        )
    else:
        print_warning("No package.json found, skipping npm tests")

    # P3: Build check
    print_header("P3: BUILD")
    if npm.exists():
        results.append(run_check("Build", ["npm", "run", "build"], timeout=300))

    all_passed = print_summary(results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
