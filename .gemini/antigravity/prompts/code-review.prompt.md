---
mode: ask
description: Comprehensive code review checklist
---

# Code Review Checklist

## Correctness
- [ ] Logic handles edge cases (empty, null, boundary)
- [ ] Error handling present and correct
- [ ] No off-by-one errors
- [ ] Async operations properly awaited

## Security
- [ ] No hardcoded secrets, API keys, tokens
- [ ] User input validated (type, length, format, range)
- [ ] SQL uses parameterized queries
- [ ] No XSS vectors (innerHTML, dangerouslySetInnerHTML)
- [ ] No command injection (shell=True, eval with user input)

## Quality
- [ ] Follows project conventions
- [ ] No commented-out code
- [ ] Clear, descriptive names
- [ ] Comments explain WHY, not WHAT
- [ ] No duplicate logic

## Report
```
CODE REVIEW — Verdict: APPROVE / NEEDS FIXES
[Bugs] <file>:<line> — <desc>
[Security] <file>:<line> — <desc>
[Quality] <file>:<line> — <desc>
```
