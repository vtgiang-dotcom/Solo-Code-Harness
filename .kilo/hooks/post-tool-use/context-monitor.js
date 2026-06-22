#!/usr/bin/env node
/**
 * context-monitor.js — PostToolUse hook for Solo-Code-Harness
 *
 * Three-phase context management (OBSERVE-ONLY — never modifies tool output):
 *   Phase 1 — Monitor: warn at 60/85 tool calls, detect tool loops
 *   Phase 2 — Output Observer: detect large outputs from Bash/Grep/Glob,
 *     save full copies to .kilo/state/tool-outputs/ for human audit,
 *     warn via stderr. Model ALWAYS receives complete output.
 *   Phase 3 — Compact Suggest: at 85% context threshold, suggest compaction
 *
 * Design: PostToolUse hooks must never truncate tool responses.
 * Truncating mid-output breaks model reasoning — critical data
 * (error messages, test failures, file paths) would be lost.
 * The model needs complete data for correct decisions.
 *
 * Exit codes:
 *   0 = Normal
 */

'use strict';

const fs = require('fs');
const path = require('path');

const STATE_DIR = path.join(process.cwd(), '.kilo', 'state');
const OUTPUT_DIR = path.join(STATE_DIR, 'tool-outputs');
const COUNTER_FILE = path.join(STATE_DIR, 'tool-count.json');
const TOKEN_LOG_FILE = path.join(STATE_DIR, 'token-log.jsonl');

// ─── Configuration ───────────────────────────────────────────────────────────
const LOOP_DETECTION_WINDOW = 10;
const TOOL_CALL_WARN_1 = 60;    // First warning threshold
const TOOL_CALL_WARN_2 = 85;    // Second warning + compact suggestion
const RECENT_TOOLS_MAX = 50;

const OUTPUT_TRIM_LINES = 1000; // Trim tool output longer than this

// Tools that produce high-volume output — trim their results
const HIGH_OUTPUT_TOOLS = ['Bash', 'Grep', 'Glob'];

// Tools that form a loop when repeated
const LOOP_PRONE_TOOLS = ['Read', 'Glob', 'Grep', 'Bash'];

// ─── Helpers ─────────────────────────────────────────────────────────────────

function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function loadState() {
  try {
    if (fs.existsSync(COUNTER_FILE)) {
      return JSON.parse(fs.readFileSync(COUNTER_FILE, 'utf8'));
    }
  } catch {}
  return { totalCalls: 0, recentTools: [], lastWarn1At: 0, lastWarn2At: 0, estimatedTokens: 0 };
}

function saveState(state) {
  ensureDir(STATE_DIR);
  fs.writeFileSync(COUNTER_FILE, JSON.stringify(state, null, 2));
}

function logTokenUsage(toolName, charCount) {
  // Rough estimation: 1 token ≈ 4 chars for English text
  const estimatedTokens = Math.round(charCount / 4);
  ensureDir(STATE_DIR);
  const entry = JSON.stringify({
    ts: new Date().toISOString(),
    tool: toolName,
    chars: charCount,
    tokens: estimatedTokens,
  });
  fs.appendFileSync(TOKEN_LOG_FILE, entry + '\n');
}

/**
 * Estimate token count from tool input/output length.
 * Uses char-based approximation: 1 token ≈ 4 chars.
 */
function estimateTokens(data) {
  if (!data) return 0;
  const raw = typeof data === 'string' ? data : JSON.stringify(data);
  return Math.round(raw.length / 4);
}

// ─── Phase 1: Monitor ────────────────────────────────────────────────────────

function checkToolLoop(recentTools) {
  if (recentTools.length < LOOP_DETECTION_WINDOW) return null;

  const lastN = recentTools.slice(-LOOP_DETECTION_WINDOW);
  const uniqueTools = new Set(lastN);

  if (uniqueTools.size <= 2) {
    const loopProne = lastN.filter(t => LOOP_PRONE_TOOLS.includes(t));
    if (loopProne.length >= LOOP_DETECTION_WINDOW * 0.8) {
      return lastN.join(', ');
    }
  }

  return null;
}

// ─── Phase 2: Output Trim ────────────────────────────────────────────────────

/**
 * Check if tool output exceeds OUTPUT_TRIM_LINES and warn.
 * DOES NOT modify output — model always sees full data.
 * Saves full output to .kilo/state/tool-outputs/ for human audit.
 * Returns metadata about the trim, or null if output is within limits.
 *
 * Design: PostToolUse hooks should NEVER modify tool output.
 * Truncating tool responses breaks model reasoning — the model needs
 * complete data to make correct decisions. Instead, we observe size,
 * save full copies for audit, and warn via stderr so the human knows
 * context is growing.
 */
function checkToolOutputSize(toolName, toolInput) {
  if (!HIGH_OUTPUT_TOOLS.includes(toolName)) return null;

  // Extract the output from the tool input.
  // Kilo Code PostToolUse events wrap the response in tool_response,
  // not tool_output. Also attempt raw tool_input for forward compatibility.
  const output = toolInput.tool_response || toolInput.tool_output || toolInput.output || toolInput.result || '';
  const outputStr = typeof output === 'string' ? output : JSON.stringify(output, null, 2);
  const lines = outputStr.split('\n');

  if (lines.length <= OUTPUT_TRIM_LINES) return null;

  ensureDir(OUTPUT_DIR);
  const ts = Date.now();
  const safeName = toolName.replace(/[^a-zA-Z0-9_-]/g, '_');
  const filename = `${safeName}-${ts}.txt`;
  const filePath = path.join(OUTPUT_DIR, filename);

  fs.writeFileSync(filePath, outputStr, 'utf8');

  const totalLines = lines.length;
  const firstLine = lines[0] ? lines[0].substring(0, 80) : '';
  const lastLine = lines[totalLines - 1] ? lines[totalLines - 1].substring(0, 80) : '';

  return {
    filename,
    totalLines,
    firstLine,
    lastLine,
  };
}

// ─── Main ────────────────────────────────────────────────────────────────────
let raw = '';

process.stdin.setEncoding('utf8');
process.stdin.resume();
process.stdin.on('data', chunk => { raw += chunk; });
process.stdin.on('end', () => {
  const state = loadState();

  let input;
  try {
    input = JSON.parse(raw);
  } catch {
    process.stdout.write(raw);
    process.exit(0);
  }

  const toolName = input.tool_name || '';

  // ── Update counters ──
  state.totalCalls++;
  state.recentTools.push(toolName);
  if (state.recentTools.length > RECENT_TOOLS_MAX) {
    state.recentTools = state.recentTools.slice(-RECENT_TOOLS_MAX);
  }

  // Track token estimate
  const toolTokens = estimateTokens(raw);
  state.estimatedTokens = (state.estimatedTokens || 0) + toolTokens;
  logTokenUsage(toolName, raw.length);

  // ── Phase 1: Monitor warnings ──
  if (state.totalCalls === TOOL_CALL_WARN_1 && state.lastWarn1At === 0) {
    process.stderr.write(
      `\n[ContextMonitor] ${TOOL_CALL_WARN_1} tool calls reached.\n` +
      `  ~${state.estimatedTokens.toLocaleString()} tokens used. Consider focusing scope.\n\n`
    );
    state.lastWarn1At = state.totalCalls;
  }

  if (state.totalCalls >= TOOL_CALL_WARN_2 &&
      (state.totalCalls - (state.lastWarn2At || 0)) >= 15) {
    process.stderr.write(
      `\n[ContextMonitor] ⚠ ${state.totalCalls} tool calls — context may be exhausted.\n` +
      `  ~${state.estimatedTokens.toLocaleString()} estimated tokens.\n` +
      `  Suggest compacting context or starting a new session.\n\n`
    );
    state.lastWarn2At = state.totalCalls;
  }

  // ── Phase 1: Tool loop detection ──
  const loopTools = checkToolLoop(state.recentTools);
  if (loopTools) {
    process.stderr.write(
      `\n[ContextMonitor] ⚠ Potential tool loop detected!\n` +
      `  Recent calls: ${loopTools}\n` +
      `  Consider breaking the loop or re-evaluating your approach.\n\n`
    );
  }

  // ── Phase 2: Observe large tool outputs (DO NOT modify) ──
  // We NEVER truncate tool output before the model sees it.
  // Truncating mid-output breaks model reasoning — critical data
  // (error messages, test failures, file paths) can be lost.
  // Instead, save a full copy for audit and warn the human.
  const sizeCheck = checkToolOutputSize(toolName, input);
  if (sizeCheck) {
    process.stderr.write(
      `\n[ContextMonitor] Large tool output detected (${sizeCheck.totalLines.toLocaleString()} lines).\n` +
      `  First: "${sizeCheck.firstLine}..."\n` +
      `  Last:  "${sizeCheck.lastLine}..."\n` +
      `  Full output saved: .kilo/state/tool-outputs/${sizeCheck.filename}\n` +
      `  Model receives full data — context may be under pressure.\n\n`
    );
  }

  // Always pass through original output unchanged
  process.stdout.write(raw);

  saveState(state);
  process.exit(0);
});
