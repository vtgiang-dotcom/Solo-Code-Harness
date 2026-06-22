#!/usr/bin/env node
/**
 * governance-capture.js — PreToolUse/PostToolUse hook for Solo-Code-Harness
 *
 * Structured approval governance with audit-ready decision trails.
 * Upgraded from ECC's governance-capture.js (v3.1.0).
 *
 * Records:
 *   1. secret_detected     — hardcoded secrets in tool input/output
 *   2. approval_requested  — destructive ops requiring explicit approval
 *   3. policy_violation    — sensitive file access, config changes
 *   4. decision_contract   — falsifiable contract recording scope of approval
 *
 * Enable: Set SOLOCODE_GOVERNANCE=0 to disable (default: enabled)
 *
 * Exit codes:
 *   0 = pass-through (event logged, no blocking)
 */

'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const MAX_STDIN = 1024 * 1024;

// Log file for governance events (in project root .kilo/logs/)
const LOG_DIR = path.join(process.cwd(), '.kilo', 'logs');

// ── Detection Patterns ──────────────────────────────────────────────────────

const SECRET_PATTERNS = [
  { name: 'aws_key', pattern: /(?:AKIA|ASIA)[A-Z0-9]{16}/i },
  { name: 'generic_secret', pattern: /(?:secret|password|token|api[_-]?key)\s*[:=]\s*["'][^"']{8,}/i },
  { name: 'private_key', pattern: /-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----/ },
  { name: 'jwt', pattern: /eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/ },
  { name: 'github_token', pattern: /gh[pousr]_[A-Za-z0-9_]{36,}/ },
];

const APPROVAL_COMMANDS = [
  { name: 'force_push', pattern: /git\s+push\s+.*--force/ },
  { name: 'reset_hard', pattern: /git\s+reset\s+--hard/ },
  { name: 'rm_force', pattern: /rm\s+-rf?\s/ },
  { name: 'drop_table', pattern: /DROP\s+(?:TABLE|DATABASE)/i },
  { name: 'delete_all', pattern: /DELETE\s+FROM\s+\w+\s*;?\s*$/i },
];

const SENSITIVE_PATHS = [
  /\.env(?:\.|$)/,
  /credentials/i,
  /secrets?\./i,
  /\.pem$/,
  /\.key$/,
  /id_rsa/,
];

// ── Helpers ─────────────────────────────────────────────────────────────────

function generateEventId() {
  return `gov-${Date.now()}-${crypto.randomBytes(4).toString('hex')}`;
}

function hashContent(content) {
  if (!content || typeof content !== 'string') return null;
  return crypto.createHash('sha256').update(content).digest('hex').slice(0, 16);
}

function detectSecrets(text) {
  if (!text || typeof text !== 'string') return [];
  return SECRET_PATTERNS.filter(({ pattern }) => pattern.test(text)).map(({ name }) => name);
}

function detectApprovalRequired(command) {
  if (!command || typeof command !== 'string') return [];
  return APPROVAL_COMMANDS.filter(({ pattern }) => pattern.test(command)).map(({ name }) => name);
}

function detectSensitivePath(filePath) {
  if (!filePath || typeof filePath !== 'string') return false;
  return SENSITIVE_PATHS.some(pattern => pattern.test(filePath));
}

function writeEvent(event) {
  try {
    if (!fs.existsSync(LOG_DIR)) {
      fs.mkdirSync(LOG_DIR, { recursive: true });
    }
    const logFile = path.join(LOG_DIR, 'governance-events.jsonl');
    fs.appendFileSync(logFile, JSON.stringify(event) + '\n');
  } catch (err) {
    process.stderr.write(`[governance] write failed: ${err.message}\n`);
  }
}

/**
 * Build a falsifiable decision contract for destructive operations.
 * Records: what was requested, scope, risk level, and evidence hash.
 * This is the core of structured approval governance (inspired by Haft/Sponsio).
 */
function buildContract(toolName, command, filePath, riskLevel) {
  return {
    contract_id: generateEventId(),
    tool: toolName,
    action: command ? command.slice(0, 200) : filePath ? `access:${filePath.slice(0, 200)}` : 'unknown',
    scope: command ? 'system_command' : 'file_operation',
    risk: riskLevel,           // 'critical' | 'high' | 'warning'
    evidence_hash: hashContent(command || filePath),
    constraints: {
      // Record what was NOT included in the approval scope
      excludes_system_dirs: true,
      excludes_credential_files: true,
      single_operation_only: true,
    },
    approver: process.env.USER || process.env.USERNAME || 'unknown',
    approved_at: new Date().toISOString(),
  };
}

// ── Main ────────────────────────────────────────────────────────────────────

let raw = '';
let truncated = false;

process.stdin.setEncoding('utf8');
process.stdin.resume();
process.stdin.on('data', chunk => {
  if (raw.length < MAX_STDIN) {
    const remaining = MAX_STDIN - raw.length;
    raw += chunk.substring(0, remaining);
    if (chunk.length > remaining) truncated = true;
  } else {
    truncated = true;
  }
});

process.stdin.on('end', () => {
  // Always pass through tool output
  process.stdout.write(raw);

  // Governance can be disabled via env var (on by default since v3.1.0)
  if (String(process.env.SOLOCODE_GOVERNANCE || '').toLowerCase() === '0') {
    process.exit(0);
  }

  const sessionId = process.env.KILO_SESSION_ID || process.env.CLAUDE_SESSION_ID || 'unknown';
  const hookPhase = process.env.HOOK_EVENT_NAME || 'unknown';

  if (truncated) {
    writeEvent({
      id: generateEventId(),
      session_id: sessionId,
      event_type: 'hook_input_truncated',
      phase: hookPhase,
      payload: { size_limit_bytes: MAX_STDIN, severity: 'warning' },
      timestamp: new Date().toISOString(),
    });
    process.exit(0);
  }

  let input;
  try {
    input = JSON.parse(raw);
  } catch {
    process.exit(0);
  }

  const toolName = input.tool_name || '';
  const toolInput = input.tool_input || {};
  const toolOutput = typeof input.tool_output === 'string' ? input.tool_output : '';

  // ── 1. Secret Detection ──
  const inputText = typeof toolInput === 'object' ? JSON.stringify(toolInput) : String(toolInput);
  const inputSecrets = detectSecrets(inputText);
  const outputSecrets = detectSecrets(toolOutput);
  const allSecrets = [...new Set([...inputSecrets, ...outputSecrets])];

  if (allSecrets.length > 0) {
    writeEvent({
      id: generateEventId(),
      session_id: sessionId,
      event_type: 'secret_detected',
      phase: hookPhase,
      payload: {
        tool: toolName,
        secret_types: allSecrets,
        severity: 'critical',
        content_hash: hashContent(inputText),
      },
      timestamp: new Date().toISOString(),
    });
  }

  // Cross-platform shell tool names
  const SHELL_TOOLS = new Set([
    'Bash', 'bash', 'run_command', 'execute',
    'runCommand', 'terminal', 'execute_command', 'shell', 'RunCommand',
  ]);

  // ── 2. Approval-Required Commands (with decision contracts) ──
  if (SHELL_TOOLS.has(toolName)) {
    const command = toolInput.command || toolInput.CommandLine || toolInput.cmd || toolInput.commandLine || '';
    const approvals = detectApprovalRequired(command);

    if (approvals.length > 0) {
      // Determine risk level
      const isForce = /--force|-f\b|reset\s+--hard/i.test(command);
      const isDataDestructive = /DROP|TRUNCATE|DELETE\s+FROM/i.test(command);
      const severity = isDataDestructive ? 'critical' : isForce ? 'high' : 'warning';

      const contract = buildContract(toolName, command, null, severity);

      writeEvent({
        id: generateEventId(),
        session_id: sessionId,
        event_type: 'decision_contract',
        phase: hookPhase,
        payload: {
          tool: toolName,
          approvals,
          severity,
          command_hash: hashContent(command),
          contract,
        },
        timestamp: new Date().toISOString(),
      });
    }
  }

  // ── 3. Sensitive File Access ──
  const filePath = toolInput.file_path || toolInput.path || toolInput.TargetFile || toolInput.AbsolutePath || toolInput.DirectoryPath || toolInput.uri || '';
  if (filePath && detectSensitivePath(filePath)) {
    writeEvent({
      id: generateEventId(),
      session_id: sessionId,
      event_type: 'policy_violation',
      phase: hookPhase,
      payload: {
        tool: toolName,
        file_path: filePath.slice(0, 200),
        reason: 'sensitive_file_access',
        severity: 'warning',
        contract: buildContract(toolName, null, filePath, 'warning'),
      },
      timestamp: new Date().toISOString(),
    });
  }

  process.exit(0);
});
