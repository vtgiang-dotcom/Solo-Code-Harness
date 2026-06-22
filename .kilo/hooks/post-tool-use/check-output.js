#!/usr/bin/env node
/**
 * check-output.js — PostToolUse hook for Solo-Code-Harness
 *
 * Checks Bash command output for error patterns. Catches common mistakes
 * visible in stderr: missing modules, syntax errors, failed tests.
 * Ported from Claude Code version check_output.py.
 *
 * Exit codes: always 0 (non-blocking, stderr warnings only)
 */

'use strict';

const ERROR_PATTERNS = [
  { name: 'Python import error', pattern: /ModuleNotFoundError|ImportError/,
    hint: 'Missing Python dependency — install the package?' },
  { name: 'Node module not found', pattern: /cannot find module/i,
    hint: 'Node module not found — run npm install?' },
  { name: 'Command not found', pattern: /command not found/i,
    hint: 'Command not found — install the tool first?' },
  { name: 'Permission denied', pattern: /Permission denied/i,
    hint: 'Permission denied — check file permissions' },
  { name: 'Not a git repo', pattern: /fatal: not a git repository/i,
    hint: 'Not a git repo — cd to correct directory?' },
  { name: 'npm error', pattern: /npm ERR!/i,
    hint: 'npm error — check package.json and node_modules' },
  { name: 'Syntax error', pattern: /SyntaxError/,
    hint: 'Syntax error in code — check for typos' },
  { name: 'Access denied', pattern: /EACCES/,
    hint: 'Access denied — check permissions or use elevated shell' },
  { name: 'File not found', pattern: /No such file or directory/i,
    hint: 'File not found — verify the path' },
  { name: 'Circular dependency', pattern: /Circular dependency/i,
    hint: 'Circular dependency detected — restructure imports' },
  { name: 'Memory error', pattern: /Out of memory|heap out of memory|MemoryError/i,
    hint: 'Out of memory — reduce data size or add pagination' },
  { name: 'Timeout', pattern: /timeout|ETIMEDOUT|ESOCKETTIMEDOUT/i,
    hint: 'Operation timed out — check network or add retry logic' },
];

let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.resume();
process.stdin.on('data', chunk => { raw += chunk; });
process.stdin.on('end', () => {
  process.stdout.write(raw);

  let input = {};
  try { input = JSON.parse(raw); } catch { process.exit(0); }

  // Only check Bash tool output
  if (!['Bash', 'bash'].includes(input.tool_name)) {
    process.exit(0);
  }

  // Check stderr from tool_response
  const toolResponse = input.tool_response || '';
  const toolOutput = input.tool_output || '';

  // Also check raw response for error indicators
  let textToCheck = '';
  if (typeof toolResponse === 'string') textToCheck += toolResponse;
  if (typeof toolOutput === 'string') textToCheck += toolOutput;

  if (!textToCheck) process.exit(0);

  for (const { name, pattern, hint } of ERROR_PATTERNS) {
    if (pattern.test(textToCheck)) {
      process.stderr.write(`[OutputCheck] ${name}: ${hint}\n`);
      // Only report first match to avoid noise
      break;
    }
  }

  process.exit(0);
});
