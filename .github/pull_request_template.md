## Description

<!-- What does this PR do? 1-2 sentences. -->

## Type

- [ ] `feat` — New feature
- [ ] `fix` — Bug fix
- [ ] `refactor` — Code restructure (no behavior change)
- [ ] `docs` — Documentation only
- [ ] `test` — Test coverage
- [ ] `chore` — Maintenance, CI, dependencies

## Verification

<!-- All gates must pass. Run `python .github/scripts/checklist.py .` -->

- [ ] `python .github/scripts/security_scan.py .` passes
- [ ] `ruff check .` passes
- [ ] Harness Eval (`python .github/scripts/eval_harness.py .`) passes
- [ ] Guard Tests (`python -m pytest tools/test_claude_guard.py -q`) pass
- [ ] Pre-commit hooks run clean

## Scope

<!-- Describe what changed and why. Reference issues if applicable. -->
