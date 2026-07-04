/**
 * Bug-reproduction tests — RED by design.
 *
 * Port pattern from codebase-memory-mcp (tests/repro/ + Makefile.cbm:419-473).
 * Each test is expected to FAIL until the bug is fixed. These tests
 * are NON-GATING — they do NOT block CI.
 *
 * After fixing a bug, move the test to test-guard.mjs as normal.
 *
 * Usage (non-gating):
 *   node .opencode/tests/repro/test-repro.mjs
 *   # Expected: exit code 1 (all tests intentionally fail)
 */

const BLOCK_PATTERNS = [
  { name: 'rm_root', pattern: /rm\s+-rf?\s+\/(?:\s|$|\*|"|')/ },
  { name: 'rm_system_dir', pattern: /rm\s+-rf?\s+\/(?:etc|usr|var|bin|lib(?:64)?|boot|sbin|opt|root|sys|proc|dev)(?:\/|\s|$)/ },
  { name: 'drop_table', pattern: /DROP\s+(?:TABLE|DATABASE)/i },
  { name: 'shutdown_system', pattern: /(?:shutdown|reboot|halt)\b/ },
  { name: 'curl_pipe_shell', pattern: /(?:curl|wget)\s+.*\|\s*(?:ba)?sh\b/ },
];

function normalizeCommand(command) {
  if (!command || typeof command !== 'string') return '';
  let cmd = command;
  cmd = cmd.replace(/\s+/g, ' ').trim();
  let prev;
  do {
    prev = cmd;
    cmd = cmd.replace(/^sudo\s+/, '');
    cmd = cmd.replace(/^env(\s+[\w]+=[^\s]*)+\s+/, '');
    cmd = cmd.replace(/^(?:bash|sh)\s+-c\s+/, '');
    cmd = cmd.replace(/^(['"])(.*)\1$/, '$2');
  } while (cmd !== prev);
  return cmd;
}

function isBlocked(cmd) {
  const normalized = normalizeCommand(cmd);
  for (const { name, pattern } of BLOCK_PATTERNS) {
    try {
      if (pattern.test(cmd) || pattern.test(normalized)) return name;
    } catch (_) {}
  }
  return null;
}

/**
 * REPRODUCTION TESTS — expected to FAIL.
 *
 * Each entry: [command, current_behavior, expected_fix, bug_id]
 * Current behavior: true = blocked, false = not blocked
 * Expected fix: what should happen after the bug is resolved
 */
const reproCases = [
  // REPRO-001: Heredoc command substitution bypass
  { bugId: 'REPRO-001', cmd: 'bash <<< "$(echo rm -rf /etc)"', expectNow: false, shouldBlock: true,
    description: 'NormalizeCommand should process command substitution inside heredocs' },

  // REPRO-002: Null byte bypass
  { bugId: 'REPRO-002', cmd: 'rm -rf /etc\\u0000hidden', expectNow: false, shouldBlock: true,
    description: 'Null byte in path should not bypass rm_system_dir check' },

  // REPRO-003: Base64-encoded destructive command
  { bugId: 'REPRO-003', cmd: 'echo "cm0gLXJmIC8=" | base64 -d', expectNow: false, shouldBlock: true,
    description: 'Base64-encoded rm -rf / — decode-and-check pipeline should be implemented' },

  // REPRO-004: Unicode homoglyph bypass
  { bugId: 'REPRO-004', cmd: 'rｍ -rf /etc', expectNow: false, shouldBlock: true,
    description: 'Fullwidth Unicode characters (U+FF4D) should be normalized to ASCII before matching' },
];

let pass = 0, fail = 0;
const failureDetails = [];

for (const { bugId, cmd, expectNow, description } of reproCases) {
  const hit = isBlocked(cmd);
  const actuallyBlocked = hit !== null;

  // REPRO TEST: we assert that the current behavior is WRONG
  // If it already blocks correctly → bug was FIXED (surprise pass)
  const bugStillExists = actuallyBlocked === expectNow;

  if (bugStillExists) {
    fail++;
    failureDetails.push({ bugId, cmd, description, hit });
    console.log(`REPRO-FAIL | [${bugId}] ${cmd} — ${description}`);
  } else {
    pass++;
    console.log(`FIXED      | [${bugId}] ${cmd} — BUG RESOLVED (move to test-guard.mjs)`);
  }
}

console.log();
console.log(`=== Repro Results: ${pass} fixed, ${fail} still broken ===`);
console.log(`Pattern tested: ${BLOCK_PATTERNS.length}`);
console.log(`Repro cases: ${reproCases.length}`);

if (fail > 0) {
  console.log('\n--- Known Bugs ---');
  for (const f of failureDetails) {
    console.log(`  ${f.bugId}: ${f.description}`);
    console.log(`    Command: ${f.cmd}`);
  }
}

// Exit 0 — repro tests are NON-GATING by design
process.exit(0);
