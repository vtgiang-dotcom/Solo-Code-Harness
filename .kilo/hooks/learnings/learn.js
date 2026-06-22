#!/usr/bin/env node
/**
 * learn.js — Continual Learning Hook for Solo-Code-Harness
 *
 * Two-tier persistent memory across sessions:
 *   Global: ~/.kilo/learnings/    (cross-project insights)
 *   Local:  .kilo/learnings/db/    (per-project conventions)
 *
 * Three lifecycle events:
 *   sessionStart  → Load top learnings, surface as systemMessage
 *   postToolUse   → Log tool outcome (~1ms overhead)
 *   sessionEnd    → Analyze failure patterns, persist insights, compact old data
 *
 * Ported from Microsoft Skills continual-learning hook.
 *
 * Exit codes: always 0 (non-blocking)
 *
 * Usage:
 *   node .kilo/hooks/learnings/learn.js sessionStart
 *   node .kilo/hooks/learnings/learn.js postToolUse
 *   node .kilo/hooks/learnings/learn.js sessionEnd
 */

'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

// ─── Configuration ──────────────────────────────────────────────────────────
const GLOBAL_DIR = path.join(os.homedir(), '.kilo', 'learnings');
const LEARNINGS_FILE = 'learnings.json';
const TOOL_LOG_FILE = 'tool-log.jsonl';
const MAX_LOG_LINES = 1000;
const DECAY_DAYS = 60;
const DECAY_MIN_HITS = 3;
const FAILURE_THRESHOLD = 3; // Same tool fails this many times → store learning

// ─── Helpers ────────────────────────────────────────────────────────────────

function ensureDir(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function repoName() {
  try {
    const { execSync } = require('child_process');
    const top = execSync('git rev-parse --show-toplevel', { encoding: 'utf8', timeout: 3000, windowsHide: true }).trim();
    return path.basename(top);
  } catch {
    return path.basename(process.cwd());
  }
}

function readJSON(filePath, fallback) {
  try {
    if (fs.existsSync(filePath)) return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch {}
  return fallback;
}

function writeJSON(filePath, data) {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
}

function appendJSONL(filePath, entry) {
  ensureDir(path.dirname(filePath));
  fs.appendFileSync(filePath, JSON.stringify(entry) + '\n');
}

function daysAgo(isoString) {
  const diff = Date.now() - new Date(isoString).getTime();
  return diff / (1000 * 60 * 60 * 24);
}

function nowISO() {
  return new Date().toISOString();
}

function generateId() {
  return `learn-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

// ─── Two-Tier DB Helpers ────────────────────────────────────────────────────

function globalDB() {
  ensureDir(GLOBAL_DIR);
  return path.join(GLOBAL_DIR, LEARNINGS_FILE);
}

function localDB() {
  // Only activate inside a git repo
  const gitDir = path.join(process.cwd(), '.git');
  if (!fs.existsSync(gitDir)) return null;
  const dir = path.join(process.cwd(), '.kilo', 'learnings', 'db');
  ensureDir(dir);
  return path.join(dir, LEARNINGS_FILE);
}

/**
 * Upsert a learning: increment hit_count if exists, else insert.
 * Returns the updated learning object.
 */
function upsertLearning(dbPath, scope, category, content, source) {
  const db = readJSON(dbPath, []);
  const now = nowISO();

  // Try to find existing matching learning (same content)
  let existing = db.find(l => l.scope === scope && l.content === content);
  if (existing) {
    existing.hit_count = (existing.hit_count || 1) + 1;
    existing.last_seen = now;
    if (source) existing.source = source;
  } else {
    existing = {
      id: generateId(),
      scope,
      category,
      content,
      source: source || 'auto',
      created_at: now,
      last_seen: now,
      hit_count: 1,
    };
    db.push(existing);
  }
  writeJSON(dbPath, db);
  return existing;
}

/**
 * Get top learnings for a scope, ordered by hit_count desc.
 */
function topLearnings(dbPath, scope, limit) {
  const db = readJSON(dbPath, []);
  return db
    .filter(l => l.scope === scope)
    .sort((a, b) => (b.hit_count || 1) - (a.hit_count || 1))
    .slice(0, limit);
}

/**
 * Compact: remove old low-value learnings and decay tool log.
 */
function compactDB(dbPath) {
  const db = readJSON(dbPath, []);
  const cutoff = DECAY_DAYS;
  const minHits = DECAY_MIN_HITS;

  const filtered = db.filter(l => {
    const age = daysAgo(l.last_seen || l.created_at);
    const hits = l.hit_count || 1;
    // Remove if older than cutoff AND low hit count
    if (age > cutoff && hits < minHits) return false;
    return true;
  });

  if (filtered.length < db.length) {
    writeJSON(dbPath, filtered);
    return db.length - filtered.length;
  }
  return 0;
}

/**
 * Rotate tool log file — keep only last N lines.
 */
function rotateToolLog(logPath) {
  if (!fs.existsSync(logPath)) return;
  try {
    const lines = fs.readFileSync(logPath, 'utf8').trim().split('\n').filter(Boolean);
    if (lines.length > MAX_LOG_LINES) {
      const trimmed = lines.slice(-MAX_LOG_LINES);
      fs.writeFileSync(logPath, trimmed.join('\n') + '\n');
    }
  } catch {}
}

// ─── Event Handlers ─────────────────────────────────────────────────────────

/**
 * SESSION START — Load and surface prior learnings.
 */
function onSessionStart() {
  const globalPath = globalDB();
  const localPath = localDB();
  let messages = [];

  // Global learnings
  const globalTop = topLearnings(globalPath, 'global', 5);
  if (globalTop.length > 0) {
    const lines = globalTop.map(l => `  • [${l.category}] ${l.content} (×${l.hit_count})`);
    messages.push(`🧠 Prior global insights (${readJSON(globalPath, []).filter(l => l.scope === 'global').length} total):`);
    messages = messages.concat(lines);
  }

  // Local learnings
  if (localPath) {
    const localTop = topLearnings(localPath, 'local', 5);
    if (localTop.length > 0) {
      messages.push('');
      messages.push(`Repo: ${repoName()} (${readJSON(localPath, []).filter(l => l.scope === 'local').length} total):`);
      messages = messages.concat(localTop.map(l => `  • [${l.category}] ${l.content} (×${l.hit_count})`));
    }
  }

  let systemMessage = '';
  if (messages.length === 0) {
    systemMessage = '🧠 Continual learning active — building knowledge from this session.';
  } else {
    systemMessage = messages.join('\n');
  }

  process.stderr.write(systemMessage + '\n');

  // Return as JSON for stdout (hook protocol)
  const result = { systemMessage };
  process.stdout.write(JSON.stringify(result));
}

/**
 * POST TOOL USE — Log tool outcome (lightweight, ~1ms).
 */
function onPostToolUse(inputData) {
  const toolName = inputData?.tool_name || inputData?.toolName || '';
  if (!toolName) return;

  const resultType = inputData?.tool_response
    ? (typeof inputData.tool_response === 'string' && inputData.tool_response.includes('error') ? 'failure' : 'success')
    : (inputData?.tool_input?.command
        ? (inputData.exit_code === 0 ? 'success' : 'failure')
        : 'unknown');

  const logPath = path.join(GLOBAL_DIR, TOOL_LOG_FILE);
  appendJSONL(logPath, {
    tool: toolName,
    result: resultType,
    ts: nowISO(),
  });

  rotateToolLog(logPath);
}

/**
 * SESSION END — Analyze patterns, store insights, compact.
 */
function onSessionEnd() {
  const logPath = path.join(GLOBAL_DIR, TOOL_LOG_FILE);
  const globalPath = globalDB();
  const localPath = localDB();

  // Analyze tool log for failure patterns
  if (!fs.existsSync(logPath)) {
    process.stderr.write('🧠 Session ended — no tool data to analyze.\n');
    process.exit(0);
  }

  try {
    const lines = fs.readFileSync(logPath, 'utf8').trim().split('\n').filter(Boolean);
    const recentEntries = lines.map(l => {
      try { return JSON.parse(l); } catch { return null; }
    }).filter(Boolean);

    // Only analyze entries from last 4 hours
    const fourHoursAgo = Date.now() - 4 * 60 * 60 * 1000;
    const recent = recentEntries.filter(e => new Date(e.ts).getTime() > fourHoursAgo);

    const total = recent.length;
    const failures = recent.filter(e => e.result === 'failure' || e.result === 'error').length;

    // Count failures per tool
    const failCounts = {};
    for (const e of recent) {
      if (e.result === 'failure' || e.result === 'error') {
        failCounts[e.tool] = (failCounts[e.tool] || 0) + 1;
      }
    }

    // Store repeated failure patterns as global learnings
    let insightsStored = 0;
    for (const [tool, count] of Object.entries(failCounts)) {
      if (count >= FAILURE_THRESHOLD) {
        upsertLearning(
          globalPath, 'global', 'tool_insight',
          `Tool "${tool}" frequently fails — check usage patterns`,
          `auto:${new Date().toISOString().slice(0, 10)}`
        );
        insightsStored++;
      }
    }

    // Store repo-specific learnings if applicable
    if (localPath) {
      const repo = repoName();
      // Detect tool success rate anomaly
      if (total > 0) {
        const failureRate = failures / total;
        if (failureRate > 0.3 && total > 5) {
          upsertLearning(
            localPath, 'local', 'pattern',
            `High tool failure rate (${Math.round(failureRate * 100)}% of ${total} calls) — verify environment setup`,
            `auto:${repo}`
          );
          insightsStored++;
        }
      }
    }

    // Compact both DBs
    const globalRemoved = compactDB(globalPath);
    let localRemoved = 0;
    if (localPath) localRemoved = compactDB(localPath);

    const compacted = globalRemoved + localRemoved;

    let summary = `🧠 Session reflected — tools: ${total}, failures: ${failures}`;
    if (insightsStored > 0) summary += `, ${insightsStored} insight(s) stored`;
    if (compacted > 0) summary += `, ${compacted} old learning(s) compacted`;
    process.stderr.write(summary + '\n');

  } catch (err) {
    process.stderr.write(`[Learn] Session end error: ${err.message}\n`);
  }
}

// ─── Main ───────────────────────────────────────────────────────────────────
const event = process.argv[2] || '';

if (process.env.SKIP_CONTINUAL_LEARNING === 'true') {
  process.exit(0);
}

switch (event) {
  case 'sessionStart': {
    // Read stdin to pass through + optionally enrich
    let raw = '';
    process.stdin.setEncoding('utf8');
    process.stdin.resume();
    process.stdin.on('data', chunk => { raw += chunk; });
    process.stdin.on('end', () => {
      process.stdout.write(raw);
      onSessionStart();
      process.exit(0);
    });
    break;
  }

  case 'postToolUse': {
    let raw = '';
    process.stdin.setEncoding('utf8');
    process.stdin.resume();
    process.stdin.on('data', chunk => { raw += chunk; });
    process.stdin.on('end', () => {
      process.stdout.write(raw);
      let input = {};
      try { input = JSON.parse(raw); } catch {}
      onPostToolUse(input);
      process.exit(0);
    });
    break;
  }

  case 'sessionEnd': {
    let raw = '';
    process.stdin.setEncoding('utf8');
    process.stdin.resume();
    process.stdin.on('data', chunk => { raw += chunk; });
    process.stdin.on('end', () => {
      process.stdout.write(raw);
      onSessionEnd();
      process.exit(0);
    });
    break;
  }

  default:
    process.stderr.write(`[Learn] Usage: learn.js <sessionStart|postToolUse|sessionEnd>\n`);
    process.exit(0);
}
