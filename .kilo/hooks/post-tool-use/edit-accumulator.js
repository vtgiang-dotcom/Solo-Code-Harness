#!/usr/bin/env node
/**
 * edit-accumulator.js — PostToolUse hook for Solo-Code-Harness
 *
 * Records edited JS/TS/JSX/TSX file paths for batch operations
 * (format, typecheck) at session end instead of after every edit.
 * Ported from ECC's post-edit-accumulator.js.
 *
 * Exit codes:
 *   0 = Normal
 */

'use strict';

const fs = require('fs');
const path = require('path');

const STATE_DIR = path.join(process.cwd(), '.kilo', 'state');
const ACCUMULATOR_FILE = path.join(STATE_DIR, 'edited-files.json');

const EDITABLE_EXTENSIONS = new Set([
  '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '.mts', '.cts',
  '.py', '.go', '.rs', '.java', '.kt', '.swift',
  '.css', '.scss', '.less',
  '.json', '.yaml', '.yml', '.md',
]);

function ensureStateDir() {
  if (!fs.existsSync(STATE_DIR)) {
    fs.mkdirSync(STATE_DIR, { recursive: true });
  }
}

function loadFiles() {
  try {
    if (fs.existsSync(ACCUMULATOR_FILE)) {
      return JSON.parse(fs.readFileSync(ACCUMULATOR_FILE, 'utf8'));
    }
  } catch {}
  return [];
}

function saveFiles(files) {
  ensureStateDir();
  fs.writeFileSync(ACCUMULATOR_FILE, JSON.stringify(files, null, 2));
}

let raw = '';

process.stdin.setEncoding('utf8');
process.stdin.resume();
process.stdin.on('data', chunk => { raw += chunk; });
process.stdin.on('end', () => {
  process.stdout.write(raw);

  let input;
  try {
    input = JSON.parse(raw);
  } catch {
    process.exit(0);
  }

  const filePath = input?.tool_input?.file_path || input?.tool_input?.file || '';
  if (!filePath) {
    process.exit(0);
  }

  const ext = path.extname(filePath).toLowerCase();
  if (EDITABLE_EXTENSIONS.has(ext)) {
    const fullPath = path.resolve(filePath);
    const files = loadFiles();

    // Track unique files across edits in this session
    if (!files.includes(fullPath)) {
      files.push(fullPath);
      saveFiles(files);
    }
  }

  process.exit(0);
});
