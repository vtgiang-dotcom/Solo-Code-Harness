---
description: Systematic debugging — reproduce → isolate → diagnose → fix → verify
allowed-tools: Read, Grep, Glob, Bash(*)
---

# Systematic Debugging

## 1. Reproduce
- Exact error message and stack trace
- Steps to reproduce
- Does it happen consistently?

## 2. Isolate
- Minimal reproduction case
- When did it start? (check git log)
- What subsystem is involved?

## 3. Diagnose
- Form **at least 2 candidate root causes** before testing any — a single
  hypothesis "confirmed" on the first try is often confirmation bias, not
  proof
- Trace the code path for each candidate
- Check assumptions at each step
- Add targeted logging if needed
- Rule out the wrong candidates with evidence, don't just skip to the one
  that "feels right"

## 4. Fix
- Root cause identified?
- Minimal fix that addresses the root cause
- Does the fix introduce new issues?

## 5. Verify
- Original issue resolved?
- Existing tests still pass?
- Edge cases handled?

## Report
```
DEBUG REPORT
============
Symptom: <description>
Root Cause: <explanation>
Fix: <file:line> — <change>
Verified: <how confirmed>
```
