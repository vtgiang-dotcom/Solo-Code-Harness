---
description: Review code changes for correctness, security, and quality
allowed-tools: Bash(git *), Read, Grep, Glob
---

# Code Review

## Context
- Current branch: !`git branch --show-current`
- Changed files: !`git diff --name-only HEAD`

## Review Dimensions

### Correctness
- Null/undefined access, off-by-one errors, race conditions
- Error handling: present and correct?
- Edge cases: empty input, boundary values, state assumptions

### Security
- Injection risks (SQL, XSS, command)
- Hardcoded secrets or credentials
- Missing input validation

### Code Quality
- Duplicated logic → suggest reuse
- Overly complex → suggest simplification
- Consistent naming and patterns

## Report
```
CODE REVIEW
===========
[Bugs] <file>:<line> — <description>
[Security] <file>:<line> — <description>
[Quality] <file>:<line> — <description>
Verdict: APPROVE / NEEDS FIXES
```
