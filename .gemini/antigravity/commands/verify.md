---
allowed-tools: Bash(python *), Bash(ruff *), Bash(git *), Read, Grep
description: Full project verification: all gates, tests, and structure checks
---

## Context

- Current branch: !`git branch --show-current`
- Last commit: !`git log --oneline -3`

## Task

Run full verification:

### Gate 1: Security
```bash
python .github/scripts/security_scan.py .
```

### Gate 2: Lint
```bash
ruff check .
```

### Gate 3: Garden (Drift)
```bash
python tools/garden.py
```

### Gate 4: Integration Tests
```bash
python tools/test_integration.py
```

### Gate 5: Harness Tests
```bash
python -m pytest tools/ -q
```

### Gate 6: Eval Score
```bash
python tools/eval_harness.py --min-score 60
```

### Gate 7: Debug Artifacts
```bash
grep -rE '(console\.log|print\(.*debug|debugger)' --include='*.py' --include='*.ts' --include='*.js' . | grep -v node_modules | grep -v '.venv' | grep -v '.git'
```

## Report Format
```
SOLO-CODE VERIFICATION
======================
Branch: <branch>

[✓/✗] Gate 1: Security Scan
[✓/✗] Gate 2: Lint
[✓/✗] Gate 3: Garden
[✓/✗] Gate 4: Integration
[✓/✗] Gate 5: Harness Tests
[✓/✗] Gate 6: Eval Score
[✓/✗] Gate 7: Debug Artifacts

VERDICT: ALL PASS / GATE <N> FAILED
```
