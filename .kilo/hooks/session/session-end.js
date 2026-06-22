#!/usr/bin/env node
/**
 * session-end.js — SessionEnd hook for Solo-Code-Harness
 *
 * Runs at the end of every agent session.
 * - Persists session summary with token estimates
 * - Reports edited files count
 * - Warns about uncommitted changes
 * - Emits cost estimate and session health report
 */

'use strict';

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const STATE_DIR = path.join(process.cwd(), '.kilo', 'state');
const SESSION_LOG_DIR = path.join(STATE_DIR, 'sessions');
const TOKEN_LOG_FILE = path.join(STATE_DIR, 'token-log.jsonl');
const TOOL_COUNT_FILE = path.join(STATE_DIR, 'tool-count.json');
const TOOL_OUTPUTS_DIR = path.join(STATE_DIR, 'tool-outputs');
const EDITED_FILES_FILE = path.join(STATE_DIR, 'edited-files.json');

// Approximate cost per 1M tokens (deepseek pricing, adjust for your provider)
const COST_PER_1M_INPUT = 0.14;   // $0.14/1M input tokens
const COST_PER_1M_OUTPUT = 0.28;  // $0.28/1M output tokens

function exec(cmd, args) {
  return spawnSync(cmd, args, {
    encoding: 'utf8',
    cwd: process.cwd(),
    timeout: 5000,  // 5s — git on Windows/network drives can hang; keep short
    windowsHide: true,
    shell: process.platform === 'win32',  // Use shell on Windows for path resolution
  });
}

function readJSON(filePath, fallback) {
  try {
    if (fs.existsSync(filePath)) {
      return JSON.parse(fs.readFileSync(filePath, 'utf8'));
    }
  } catch {}
  return fallback;
}

/**
 * Count staged and unstaged changes. Graceful on git timeout/error.
 */
function getChangedFileCount() {
  try {
    const result = exec('git', ['diff', '--name-only']);
    const staged = exec('git', ['diff', '--cached', '--name-only']);
    const unstagedOk = result.status === 0 && !result.error;
    const stagedOk = staged.status === 0 && !staged.error;
    const unstaged = unstagedOk
      ? result.stdout.trim().split('\n').filter(Boolean).length
      : 0;
    const stagedCount = stagedOk
      ? staged.stdout.trim().split('\n').filter(Boolean).length
      : 0;
    return { staged: stagedCount, unstaged, total: stagedCount + unstaged };
  } catch {
    return { staged: 0, unstaged: 0, total: 0 };
  }
}

/**
 * Parse token log to compute session-level token stats.
 */
function getTokenStats() {
  const tokens = { totalCalls: 0, totalChars: 0, totalTokens: 0, toolBreakdown: {} };
  try {
    if (fs.existsSync(TOKEN_LOG_FILE)) {
      const lines = fs.readFileSync(TOKEN_LOG_FILE, 'utf8').trim().split('\n');
      tokens.totalCalls = lines.length;
      for (const line of lines) {
        try {
          const entry = JSON.parse(line);
          tokens.totalChars += (entry.chars || 0);
          tokens.totalTokens += (entry.tokens || 0);
          const tool = entry.tool || 'unknown';
          tokens.toolBreakdown[tool] = (tokens.toolBreakdown[tool] || 0) + (entry.tokens || 0);
        } catch {}
      }
    }
  } catch {}
  return tokens;
}

/**
 * Estimate cost based on token usage.
 * Assumes ~70% input, ~30% output split for coding agents.
 */
function estimateCost(inputTokens, outputTokens) {
  return (inputTokens / 1e6) * COST_PER_1M_INPUT + (outputTokens / 1e6) * COST_PER_1M_OUTPUT;
}

/**
 * Count trimmed output files.
 */
function getTrimmedOutputCount() {
  try {
    if (fs.existsSync(TOOL_OUTPUTS_DIR)) {
      return fs.readdirSync(TOOL_OUTPUTS_DIR).filter(f => f.endsWith('.txt')).length;
    }
  } catch {}
  return 0;
}

/**
 * Format duration in human-readable form.
 */
function formatDuration(ms) {
  const seconds = Math.round(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (minutes < 60) return `${minutes}m ${remainingSeconds}s`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}

// ─── Main ────────────────────────────────────────────────────────────────────
let raw = '';

process.stdin.setEncoding('utf8');
process.stdin.resume();
process.stdin.on('data', chunk => { raw += chunk; });
process.stdin.on('end', () => {
  process.stdout.write(raw);

  try {
    const sessionId = process.env.KILO_SESSION_ID
      || process.env.CLAUDE_SESSION_ID
      || process.env.KILO_SESSION
      || process.env.AGENT_SESSION_ID
      || `session-${Date.now()}`;
    const toolState = readJSON(TOOL_COUNT_FILE, { totalCalls: 0, estimatedTokens: 0 });
    const editedFiles = readJSON(EDITED_FILES_FILE, []);
    const changes = getChangedFileCount();
    const tokenStats = getTokenStats();
    const trimmedOutputs = getTrimmedOutputCount();

    // Load session start log
    const sessionFile = path.join(SESSION_LOG_DIR, `${sessionId.replace(/[^a-zA-Z0-9_-]/g, '_')}.json`);
    const sessionStart = readJSON(sessionFile, { startedAt: new Date().toISOString() });

    const startedAt = new Date(sessionStart.startedAt);
    const elapsedMs = Date.now() - startedAt.getTime();

    // Estimate input vs output tokens (rough split: 70/30 for coding agents)
    const totalTokens = tokenStats.totalTokens || toolState.estimatedTokens || 0;
    const inputTokens = Math.round(totalTokens * 0.7);
    const outputTokens = Math.round(totalTokens * 0.3);
    const cost = estimateCost(inputTokens, outputTokens);

    // Top 3 tools by token consumption
    const topTools = Object.entries(tokenStats.toolBreakdown)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([name, tokens]) => `${name} (${tokens.toLocaleString()} tok)`)
      .join(', ');

    // Update session log with end data
    const endLog = {
      ...sessionStart,
      sessionId,
      endedAt: new Date().toISOString(),
      elapsedMs,
      duration: formatDuration(elapsedMs),
      toolCalls: toolState.totalCalls,
      tokenLogs: tokenStats.totalCalls,
      inputTokens,
      outputTokens,
      totalTokens,
      filesEdited: editedFiles.length,
      trimmedOutputs,
      stagedChanges: changes.staged,
      unstagedChanges: changes.unstaged,
      estimatedCostUSD: cost.toFixed(4),
      topTools,
    };

    if (fs.existsSync(path.dirname(sessionFile))) {
      fs.writeFileSync(sessionFile, JSON.stringify(endLog, null, 2));
    }

    // ── Session summary report ──
    process.stderr.write('\n' + '═'.repeat(60) + '\n');
    process.stderr.write('  Solo-Code — Session Summary\n');
    process.stderr.write('═'.repeat(60) + '\n');
    process.stderr.write(
      `  Duration:    ${formatDuration(elapsedMs)}\n` +
      `  Tool calls:  ${toolState.totalCalls}\n` +
      `  Est. tokens: ${totalTokens.toLocaleString()} (~${inputTokens.toLocaleString()} in / ~${outputTokens.toLocaleString()} out)\n` +
      `  Est. cost:   $${cost.toFixed(4)}\n` +
      `  Files:       ${editedFiles.length} edited | ${trimmedOutputs} outputs trimmed\n` +
      `  Git:         ${changes.staged} staged + ${changes.unstaged} unstaged\n`
    );
    if (topTools) {
      process.stderr.write(`  Top tools:   ${topTools}\n`);
    }
    process.stderr.write('─'.repeat(60) + '\n\n');

    if (changes.total > 0) {
      process.stderr.write(`[Solo-Code] ⚠ ${changes.total} uncommitted changes. Remember to commit or stash.\n\n`);
    }

    if (trimmedOutputs > 0) {
      process.stderr.write(`[Solo-Code] ℹ ${trimmedOutputs} tool outputs were trimmed to save context. Full data in .kilo/state/tool-outputs/\n\n`);
    }
  } catch (err) {
    process.stderr.write(`[SessionEnd] Warning: ${err.message}\n`);
  }

  process.exit(0);
});
