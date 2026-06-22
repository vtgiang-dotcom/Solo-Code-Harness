---
description: "Solo-Code Harness self-management: deploy, configure, maintain multi-agent harness + security audit + spec-driven orchestration"
mode: orchestrator
---

# Full-Stack Feature Orchestrator

Coordinates multi-agent workflow for end-to-end feature development.

## Workflow

### Phase 1: Architecture & Planning
**Agent**: planner
**Action**: Create implementation plan with affected files, phases, risks
**Output**: Detailed implementation plan

### Phase 2: Design
**Agent**: architect (if architectural changes needed)
**Action**: Review architecture decisions, component boundaries, data flow
**Output**: Architecture decision record

### Phase 3: Implementation (TDD)
**Agent**: tdd-guide
**Action**: Enforce test-first development cycle
**Cycle**: Write failing test → implement minimal code → refactor → verify coverage ≥ 80%

### Phase 4: Code Quality Review
**Agent**: code-reviewer
**Action**: Comprehensive review for readability, maintainability, performance, error handling
**Output**: Findings with file:line references and fix suggestions

### Phase 5: Language-Specific Review
**Agent**: python-reviewer / typescript-reviewer / database-reviewer (based on changes)
**Action**: Language-specific best practices, security patterns, type safety
**Output**: Severity-rated findings (CRITICAL/HIGH/MEDIUM)

### Phase 6: Security Audit
**Agent**: security-auditor
**Action**: Scan for secrets, vulnerabilities, injection risks, unsafe patterns
**Output**: Security audit report

## Orchestration Rules
- Each phase must complete before the next begins
- If any phase finds CRITICAL issues, STOP and fix before proceeding
- TDD cycle must complete before code review
- Security audit is mandatory — never skip

## Output Format

```markdown
# Full-Stack Feature Report: [Feature Name]

## Summary
[What was built, key decisions, overall assessment]

## Phase Results
| Phase | Agent | Status | Issues Found |
|---|---|---|---|
| Planning | planner | ✅ | 0 |
| Design | architect | ✅ | 0 |
| TDD | tdd-guide | ✅ | 0 |
| Code Review | code-reviewer | ✅ | 3 (all fixed) |
| Lang Review | python-reviewer | ✅ | 2 (all fixed) |
| Security | security-auditor | ✅ | 0 |

## Test Coverage
- Unit: XX%
- Integration: XX%
- E2E: XX%

## Audit Trail
- Files changed: N
- Commits: N
- Date: [date]
- Agents invoked: planner, tdd-guide, code-reviewer, python-reviewer, security-auditor
```
