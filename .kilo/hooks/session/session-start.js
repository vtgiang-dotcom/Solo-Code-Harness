#!/usr/bin/env node
/**
 * session-start.js — SessionStart hook for Solo-Code-Harness
 *
 * Runs at the start of every agent session.
 * - Detects package manager (npm, yarn, pnpm, bun)
 * - Loads project context from .kilo/memory/
 * - Checks git status and branch
 * - Resets per-session state (edited files, tool counts)
 *
 * Ported from ECC's session-start-bootstrap.js concept.
 */

'use strict';

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const STATE_DIR = path.join(process.cwd(), '.kilo', 'state');
const TOOL_COUNT_FILE = path.join(STATE_DIR, 'tool-count.json');
const EDITED_FILES_FILE = path.join(STATE_DIR, 'edited-files.json');
const SESSION_LOG_DIR = path.join(STATE_DIR, 'sessions');

const MAX_STDIN = 1024 * 1024;

function exec(cmd, args) {
  return spawnSync(cmd, args, {
    encoding: 'utf8',
    cwd: process.cwd(),
    timeout: 5000,  // 5s — git on Windows/network drives can hang; keep short
    windowsHide: true,
    shell: process.platform === 'win32',  // Use shell on Windows for path resolution
  });
}

/**
 * Detect which package manager is available in the project.
 */
function detectPackageManager() {
  const checks = [
    { name: 'pnpm', file: 'pnpm-lock.yaml', cmd: 'pnpm' },
    { name: 'yarn', file: 'yarn.lock', cmd: 'yarn' },
    { name: 'bun', file: 'bun.lockb', cmd: 'bun' },
    { name: 'npm', file: 'package-lock.json', cmd: 'npm' },
  ];

  for (const { name, file, cmd } of checks) {
    if (fs.existsSync(path.join(process.cwd(), file))) {
      const result = exec(cmd, ['--version']);
      if (result.status === 0) {
        return { name, version: result.stdout.trim() };
      }
    }
  }

  return { name: 'npm', version: 'unknown' };
}

/**
 * Get git info for the session.
 */
function getGitInfo() {
  try {
    const branch = exec('git', ['rev-parse', '--abbrev-ref', 'HEAD']);
    const sha = exec('git', ['rev-parse', '--short', 'HEAD']);
    const status = exec('git', ['status', '--porcelain']);

    // Check for git errors or timeouts: treat as unknown repo state, not session failure
    const branchOk = branch.status === 0 && !branch.error && branch.stdout?.trim();
    const shaOk = sha.status === 0 && !sha.error && sha.stdout?.trim();
    const statusOk = status.status === 0 && !status.error;

    const changedFiles = statusOk
      ? status.stdout.trim().split('\n').filter(Boolean).length
      : 0;

    return {
      branch: branchOk ? branch.stdout.trim() : 'unknown',
      sha: shaOk ? sha.stdout.trim() : 'unknown',
      dirtyFiles: changedFiles,
    };
  } catch {
    return { branch: 'unknown', sha: 'unknown', dirtyFiles: 0 };
  }
}

/**
 * Ensure state directories exist.
 */
function ensureDirectories() {
  const dirs = [STATE_DIR, SESSION_LOG_DIR];
  for (const dir of dirs) {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  }
}

/**
 * Reset per-session state.
 */
function resetSessionState() {
  ensureDirectories();

  // Reset tool counter with token tracking fields
  fs.writeFileSync(TOOL_COUNT_FILE, JSON.stringify({
    totalCalls: 0,
    recentTools: [],
    lastWarningAt: 0,
    lastWarn1At: 0,
    lastWarn2At: 0,
    estimatedTokens: 0,
  }));

  // Reset edited files accumulator
  fs.writeFileSync(EDITED_FILES_FILE, JSON.stringify([]));
}

/**
 * Log session start.
 */
function logSessionStart(gitInfo, pkgManager) {
  ensureDirectories();

  const sessionId = process.env.KILO_SESSION_ID
    || process.env.CLAUDE_SESSION_ID
    || process.env.KILO_SESSION
    || process.env.AGENT_SESSION_ID
    || `session-${Date.now()}`;
  const logEntry = {
    sessionId,
    startedAt: new Date().toISOString(),
    branch: gitInfo.branch,
    sha: gitInfo.sha,
    dirtyFiles: gitInfo.dirtyFiles,
    packageManager: pkgManager.name,
    pmVersion: pkgManager.version,
    cwd: process.cwd(),
  };

  const sessionFile = path.join(SESSION_LOG_DIR, `${sessionId.replace(/[^a-zA-Z0-9_-]/g, '_')}.json`);
  fs.writeFileSync(sessionFile, JSON.stringify(logEntry, null, 2));

  process.stderr.write(
    `\n[Solo-Code] Session started\n` +
    `  Branch: ${gitInfo.branch} (${gitInfo.sha}) | ${gitInfo.dirtyFiles} dirty files\n` +
    `  Package manager: ${pkgManager.name} ${pkgManager.version}\n` +
    `  CWD: ${process.cwd()}\n\n`
  );
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
let raw = '';

process.stdin.setEncoding('utf8');
process.stdin.resume();
process.stdin.on('data', chunk => { raw += chunk; });
process.stdin.on('end', () => {
  process.stdout.write(raw);

  // Run session setup
  try {
    const gitInfo = getGitInfo();
    const pkgManager = detectPackageManager();

    resetSessionState();
    logSessionStart(gitInfo, pkgManager);

    // Set env for downstream hooks
    process.env.SOLO_PKG_MANAGER = pkgManager.name;
    process.env.SOLO_GIT_BRANCH = gitInfo.branch;
  } catch (err) {
    process.stderr.write(`[SessionStart] Warning: ${err.message}\n`);
  }

  process.exit(0);
});
