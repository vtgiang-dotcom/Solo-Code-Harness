#!/usr/bin/env node
/**
 * ralph-loop.js — Stop Hook for Solo-Code-Harness
 *
 * Implementation of the Ralph Wiggum technique: a stop hook that intercepts
 * the agent's exit attempt and re-feeds the same prompt to continue work.
 *
 * The hook reads state from .kilo/ralph/state.json to determine:
 *   - Whether a Ralph loop is active
 *   - Current iteration count
 *   - Max iterations allowed
 *   - Completion promise text
 *
 * When active: blocks exit, increments counter, returns the original prompt.
 * When complete: allows exit normally.
 *
 * Usage:
 *   node .kilo/hooks/ralph/ralph-loop.js
 *
 * Controlled via CLI command: /ralph-loop "prompt" --max-iterations N --completion-promise "TEXT"
 *
 * Exit codes:
 *   0 = Allow session to end
 *   2 = Block exit, continue looping
 */

'use strict';

const fs = require('fs');
const path = require('path');

const RALPH_DIR = path.join(process.cwd(), '.kilo', 'ralph');
const STATE_FILE = path.join(RALPH_DIR, 'state.json');

function ensureDir(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function readState() {
  try {
    if (fs.existsSync(STATE_FILE)) return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
  } catch {}
  return null;
}

function writeState(state) {
  ensureDir(RALPH_DIR);
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
}

// ─── Stop Hook Logic ────────────────────────────────────────────────────────

let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.resume();
process.stdin.on('data', chunk => { raw += chunk; });
process.stdin.on('end', () => {
  process.stdout.write(raw);

  const state = readState();
  if (!state || !state.active) {
    // No active Ralph loop — allow exit
    process.exit(0);
  }

  let input = {};
  try { input = JSON.parse(raw); } catch {}

  // Check if completion promise was emitted in the agent's stop message
  const reason = input.reason || '';
  if (state.completionPromise && reason.includes(state.completionPromise)) {
    // Agent claims completion — verify before allowing exit
    // For now, trust the agent. In production, could add verification step.
    state.active = false;
    state.stoppedAt = new Date().toISOString();
    writeState(state);
    process.stderr.write(
      `[Ralph] Completion promise detected. Loop complete after ${state.iterations} iteration(s).\n`
    );
    process.exit(0);
  }

  // Check max iterations
  const maxIter = state.maxIterations || 50;
  if (state.iterations >= maxIter) {
    state.active = false;
    state.stoppedAt = new Date().toISOString();
    writeState(state);
    process.stderr.write(
      `[Ralph] Max iterations (${maxIter}) reached. Stopping.\n`
    );
    process.exit(0);
  }

  // Blocks the exit — Ralph continues
  state.iterations = (state.iterations || 0) + 1;
  state.lastIterationAt = new Date().toISOString();
  writeState(state);

  const remaining = maxIter - state.iterations;

  const decision = {
    decision: 'block',
    reason: `[Ralph Loop — Iteration ${state.iterations}/${maxIter}] ${state.prompt}`,
    systemMessage:
      `\n🔄 **Ralph Loop** — Iteration ${state.iterations}/${maxIter} (${remaining} remaining)\n\n` +
      `${state.prompt}\n\n` +
      `You are in a self-referential loop. Your previous work persists in files and git history. ` +
      `Improve upon it. When truly done, include "${state.completionPromise}" in your stop message.\n`
  };

  process.stdout.write(JSON.stringify(decision));
  process.exit(2);
});
