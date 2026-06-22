---
allowed-tools: Bash(python *), Bash(pytest *), Bash(ruff *), Read, Grep, Glob
description: Run tests and verify code quality
---

## Context

- Current branch: !`git branch --show-current`
- Changed files: !`git diff --name-only HEAD`

## Task

### 1. Lint
```bash
ruff check .
```
Fix any lint errors before proceeding.

### 2. Unit Tests
```bash
python -m pytest tools/test_harness.py -q
```
All tests must pass.

### 3. Integration Tests
```bash
python tools/test_integration.py
```
All gates must be green.

### 4. Coverage Check
Verify that changed code paths have test coverage:
- Happy path tested?
- Error path tested?
- Edge cases tested?

### Report Format
```
TEST RESULTS
============
Lint: PASS / FAIL
Unit Tests: <N> passed, <M> failed
Integration: <N> passed, <M> failed

Verdict: ALL PASS / NEEDS FIXES
```
