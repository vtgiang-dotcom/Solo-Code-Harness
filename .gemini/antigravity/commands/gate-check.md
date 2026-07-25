---
description: Run all 7 Solo-Code verification gates
allowed-tools: Bash(python *)
---

# Gate Check

Run all verification gates in order. Stop at first failure.

## Gate 1: Security Scan
```bash
python .github/scripts/security_scan.py . --strict
```

## Gate 2: Lint
```bash
ruff check .
```

## Gate 3: Garden (Drift Detection)
```bash
python tools/garden.py --strict
```

## Gate 4: Integration Tests
```bash
python tools/test_integration.py
```

## Gate 5: Harness Tests
```bash
python -m pytest tools/ -q
```

## Gate 6: Eval Score
```bash
python tools/eval_harness.py --min-score 60
```

## Gate 7: Debug Artifacts
```bash
grep -rE '(console\.log|print\(.*debug|debugger)' --include='*.py' --include='*.ts' --include='*.js' . | grep -v node_modules | grep -v '.venv'
```

## Report
```
[✓/✗] Gate 1-7
VERDICT: ALL PASS / GATE <N> FAILED
```
