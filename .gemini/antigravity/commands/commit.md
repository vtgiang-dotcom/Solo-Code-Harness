---
allowed-tools: Bash(git *), Bash(python .github/scripts/security_scan.py:*), Read, Grep
description: Create a well-formed git commit with security scan
---

## Context

- Current branch: !`git branch --show-current`
- Staged files: !`git diff --cached --name-only`
- Unstaged changes: !`git diff --name-only`
- Diff stats: !`git diff --stat HEAD`

## Task

### 1. Stage Changes
If nothing is staged, review the working tree and stage relevant files.

### 2. Security Scan
```bash
python .github/scripts/security_scan.py .
```
If secrets found → **BLOCK the commit** until resolved.

### 3. Review Diff
Check for:
- Debug statements (console.log, print, debugger)
- Commented-out code
- Hardcoded values that should be config
- Missing error handling

### 4. Commit
```
type: concise summary (max 72 chars)

Optional body: 1-2 sentences explaining WHY.

Co-Authored-By: Solo-Code <admin@solo-code.com>
```

**Types:** feat, fix, refactor, docs, test, chore, perf

### 5. Push (if requested)
```bash
git push origin <current-branch>
```
Never force-push to main/master.
