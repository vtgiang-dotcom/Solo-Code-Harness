#!/usr/bin/env node
/**
 * security-check-post.js — PostToolUse hook for Solo-Code-Harness
 *
 * Scans git diff for secrets after commits and pushes.
 * Ported from Claude Code version security-check.py postCommit/postPush.
 *
 * Events handled:
 *   - postCommit: scan staged diff after git commit
 *   - postPush:   scan recent commits after git push
 *
 * Exit codes: always 0 (non-blocking, stderr warnings only)
 */

'use strict';

const { execSync } = require('child_process');
const path = require('path');

const HIGH_SENSITIVITY_SECRETS = [
  { name: 'Anthropic/OpenAI API key', pattern: /sk-[a-zA-Z0-9]{20,}/ },
  { name: 'AWS Access Key', pattern: /AKIA[0-9A-Z]{16}/ },
  { name: 'GitHub Token', pattern: /gh[pousr]_[A-Za-z0-9_]{36,}/ },
  { name: 'Google API Key', pattern: /AIza[0-9A-Za-z\-_]{35}/ },
  { name: 'Slack Token', pattern: /xox[bpras]-[0-9a-zA-Z]{10,}/ },
  { name: 'Private Key', pattern: /-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----/ },
  { name: 'Hardcoded password', pattern: /(?:password|passwd|pwd)\s*[:=]\s*["'][^"']{8,}["']/i },
  { name: 'Hardcoded API key', pattern: /(?:api_key|apikey|api-key|secret_key)\s*[:=]\s*["'][\w\-]{20,}["']/i },
  { name: 'JWT Token', pattern: /eyJ[a-zA-Z0-9\-_]+\.eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+/ },
  { name: 'DB connection string', pattern: /(?:mongodb|postgres|mysql|redis):\/\/[^"'\s]+@/i },
];

function scanDiff() {
  try {
    const result = execSync('git diff HEAD', {
      encoding: 'utf8',
      timeout: 30000,
      cwd: process.cwd(),
      windowsHide: true,
    });
    if (!result.trim()) return [];

    const findings = [];
    const lines = result.split('\n');
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      // Only scan added lines (starting with +), skip ++ (file header)
      if (!line.startsWith('+') || line.startsWith('+++')) continue;

      for (const { name, pattern } of HIGH_SENSITIVITY_SECRETS) {
        if (pattern.test(line)) {
          const sanitized = line.replace(pattern, '[REDACTED]').substring(0, 120);
          findings.push(`  [${name}] line ${i + 1}: ${sanitized}`);
          break; // One finding per line
        }
      }
    }
    return findings;
  } catch {
    return [];
  }
}

// ─── Main ───────────────────────────────────────────────────────────────────
let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.resume();
process.stdin.on('data', chunk => { raw += chunk; });
process.stdin.on('end', () => {
  process.stdout.write(raw);

  let input = {};
  try { input = JSON.parse(raw); } catch {}

  // Cross-platform shell tool names
  const SHELL_TOOLS = new Set(['Bash', 'bash', 'run_command', 'execute', 'runCommand', 'terminal', 'execute_command', 'shell', 'RunCommand']);

  // Only trigger on git commit or git push
  const toolName = input.tool_name || '';
  if (!SHELL_TOOLS.has(toolName)) {
    process.exit(0);
  }

  const command = (input.tool_input || {}).command || '';
  const isCommit = /\bgit\s+commit\b/.test(command);
  const isPush = /\bgit\s+push\b/.test(command);

  if (!isCommit && !isPush) {
    process.exit(0);
  }

  const findings = scanDiff();
  if (findings.length > 0) {
    const op = isCommit ? 'commit' : 'push';
    process.stderr.write(
      `\n[SecurityCheck] SECURITY ALERT after ${op}:\n` +
      findings.join('\n') +
      `\n  Remove hardcoded secrets and use environment variables.\n\n`
    );
  }

  process.exit(0);
});
