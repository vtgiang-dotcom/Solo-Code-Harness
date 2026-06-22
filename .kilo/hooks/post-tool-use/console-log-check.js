#!/usr/bin/env node
/**
 * console-log-check.js — PostToolUse hook for Solo-Code-Harness
 *
 * Warns about leftover console.log/debug statements after file edits.
 * Supports JS/TS/Python file types.
 *
 * Exit codes:
 *   0 = PASS or WARN (non-blocking)
 */

'use strict';

const fs = require('fs');
const path = require('path');

const MAX_STDIN = 1024 * 1024;

// Patterns that should not be in production code
const DEBUG_PATTERNS = {
  '.js': [
    { name: 'console.log', pattern: /console\.log\(/ },
    { name: 'console.debug', pattern: /console\.debug\(/ },
    { name: 'console.warn', pattern: /console\.warn\(/ },
    { name: 'debugger', pattern: /\bdebugger\b/ },
  ],
  '.jsx': [
    { name: 'console.log', pattern: /console\.log\(/ },
    { name: 'console.debug', pattern: /console\.debug\(/ },
    { name: 'debugger', pattern: /\bdebugger\b/ },
  ],
  '.ts': [
    { name: 'console.log', pattern: /console\.log\(/ },
    { name: 'console.debug', pattern: /console\.debug\(/ },
    { name: 'debugger', pattern: /\bdebugger\b/ },
  ],
  '.tsx': [
    { name: 'console.log', pattern: /console\.log\(/ },
    { name: 'console.debug', pattern: /console\.debug\(/ },
    { name: 'debugger', pattern: /\bdebugger\b/ },
  ],
  '.py': [
    { name: 'print()', pattern: /\bprint\(/ },
    { name: 'pdb.set_trace()', pattern: /\bpdb\.set_trace\(\)/ },
    { name: 'breakpoint()', pattern: /\bbreakpoint\(\)/ },
    { name: 'icecream ic()', pattern: /\bic\(/ },
  ],
  '.go': [
    { name: 'fmt.Println', pattern: /\bfmt\.Println\(/ },
    { name: 'log.Println', pattern: /\blog\.Println\(/ },
    { name: 'fmt.Printf', pattern: /\bfmt\.Printf\(/ },
  ],
};

function checkDebugStatements(filePath) {
  if (!filePath || !fs.existsSync(filePath)) return [];

  // Only check source files, skip generated/minified/test files
  if (filePath.includes('.min.') || filePath.includes('.generated.')) return [];
  if (filePath.includes('/__tests__/') || filePath.includes('\\.test.') || filePath.includes('\\.spec.')) return [];

  const ext = path.extname(filePath);
  const patterns = DEBUG_PATTERNS[ext] || [];
  if (patterns.length === 0) return [];

  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const lines = content.split('\n');
    const findings = [];

    for (const { name, pattern } of patterns) {
      for (let i = 0; i < lines.length; i++) {
        if (pattern.test(lines[i])) {
          // Skip if it looks like a comment line
          const trimmed = lines[i].trim();
          if (trimmed.startsWith('//') || trimmed.startsWith('#') || trimmed.startsWith('/*') || trimmed.startsWith('*')) continue;
          if (trimmed.startsWith('--') || trimmed.startsWith('REM ')) continue;

          findings.push({ name, line: i + 1, snippet: trimmed.substring(0, 80) });
        }
      }
    }

    return findings;
  } catch {
    return [];
  }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
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
  process.stdout.write(raw);

  if (truncated) {
    process.exit(0);
  }

  try {
    const input = JSON.parse(raw);
    const filePath = String(input?.tool_input?.file_path || '');
    const findings = checkDebugStatements(filePath);

    if (findings.length > 0) {
      const relative = path.relative(process.cwd(), filePath) || filePath;
      process.stderr.write(`\n[ConsoleLogCheck] Debug statements found in ${relative}:\n`);
      findings.slice(0, 5).forEach(f => {
        process.stderr.write(`  Line ${f.line}: ${f.name} — ${f.snippet}\n`);
      });
      if (findings.length > 5) {
        process.stderr.write(`  ... and ${findings.length - 5} more\n`);
      }
      process.stderr.write(`  ⚠ Remove these before committing.\n\n`);
    }
  } catch {
    // Ignore parse errors
  }

  process.exit(0);
});
