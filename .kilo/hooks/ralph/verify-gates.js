#!/usr/bin/env node
/**
 * verify-gates.js — Stop Hook for Solo-Code-Harness
 *
 * Checks if verification gates were run before the agent stops.
 * Scans the session transcript for evidence of security scan, lint,
 * checklist, and tests.
 *
 * Ported from Claude Code version check_stop.py.
 *
 * Exit codes: 0 = allow stop (reminder only, never blocks)
 */

'use strict';

const GATES = [
  { keyword: 'security_scan.py', name: 'Secret Scan', msg: 'Secret scan not detected this session' },
  { keyword: 'ruff check', name: 'Lint', msg: 'Ruff lint not detected this session' },
  { keyword: 'checklist.py', name: 'Checklist', msg: 'Checklist not run this session' },
  { keyword: 'pytest', name: 'Tests', msg: 'Tests not run this session' },
  { keyword: 'eval_harness.py', name: 'Eval', msg: 'Harness eval not run this session' },
  { keyword: 'console.log', name: 'Debug Check', msg: 'Debug statement check not run — scan for console.log' },
];

let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.resume();
process.stdin.on('data', chunk => { raw += chunk; });
process.stdin.on('end', () => {
  process.stdout.write(raw);

  const transcript = raw.toLowerCase();

  const missing = [];
  for (const { keyword, msg } of GATES) {
    if (!transcript.includes(keyword.toLowerCase())) {
      missing.push(msg);
    }
  }

  if (missing.length > 0) {
    process.stderr.write(
      `\n[VerifyGates] ⚠ Verification checks missing from this session:\n` +
      missing.map(m => `  - ${m}`).join('\n') +
      `\n  Run: python .github/scripts/checklist.py .\n\n`
    );
  }

  process.exit(0);
});
