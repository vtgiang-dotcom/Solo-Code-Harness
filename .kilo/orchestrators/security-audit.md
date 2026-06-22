---
description: "Solo-Code Harness self-management: deploy, configure, maintain multi-agent harness + security audit + spec-driven orchestration"
mode: orchestrator
---

# Security Audit Orchestrator

This orchestrator coordinates a full security audit workflow across 3 specialized agents.

## Workflow

### Phase 1: Secret Scanning
**Agent**: security-auditor
**Action**: Run `python .github/scripts/security_scan.py .` to detect hardcoded secrets
**Output**: List of secrets found (CRITICAL/HIGH/MEDIUM/LOW)

### Phase 2: Vulnerability Assessment
**Agent**: code-reviewer (in security mode)
**Action**: Scan recent diffs for OWASP Top 10 vulnerabilities
**Focus areas**:
- SQL Injection (unparameterized queries)
- XSS (dangerouslySetInnerHTML, innerHTML)
- Authentication bypass (missing middleware)
- Path traversal (unvalidated paths)
- Command injection (shell=True, eval)

### Phase 3: Architectural Security Review
**Agent**: architect
**Action**: Review system design for security weaknesses
**Check**:
- Principle of least privilege in auth
- Data encryption at rest and in transit
- API security (rate limiting, CORS, input validation)
- Third-party dependency security

## Output Format

```markdown
# Security Audit Report

## Executive Summary
[Overall security posture: Safe / Needs Attention / Critical Issues]

## Findings

### Phase 1: Secret Scanning
- 🔴 CRITICAL N / 🟡 HIGH N / 🟠 MEDIUM N / ⚪ LOW N

### Phase 2: Vulnerability Assessment
[List of vulnerabilities with severity and location]

### Phase 3: Architectural Review
[Architecture-level concerns]

## Recommendations
1. [Immediate action items]
2. [Short-term improvements]
3. [Long-term hardening]

## Audit Trail
- Scan date: [date]
- Files reviewed: [count]
- Agents invoked: security-auditor, code-reviewer, architect
```
