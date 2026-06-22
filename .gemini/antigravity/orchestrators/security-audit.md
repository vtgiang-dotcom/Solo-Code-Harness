---
description: Multi-agent security audit — secret scan → vulnerability assessment → hardening
mode: orchestrator
---

# Security Audit Orchestrator

Coordinate a full security audit across 3 specialized agents.

## Phase 1: Secret Scanning
**Agent**: security-auditor
**Action**: Run `python .github/scripts/security_scan.py .`
**Output**: List of findings, categorized by severity (CRITICAL/HIGH/MEDIUM/LOW)

## Phase 2: Vulnerability Assessment
**Agent**: code-reviewer (security mode)
**Action**: Scan recent diffs for OWASP Top 10 vulnerabilities
**Focus**: SQL Injection, XSS, authentication bypass, path traversal, command injection

## Phase 3: Hardening
**Agent**: architect
**Action**: Generate specific, actionable fixes for each finding
**Priority**: CRITICAL → HIGH → MEDIUM → LOW

## Report Format
```
SECURITY AUDIT REPORT
=====================
Secrets: <N> | Vulnerabilities: <N> | Recommendations: <N>

CRITICAL: <count> — must fix before merge
HIGH: <count> — fix this sprint
MEDIUM: <count> — track in backlog
```
