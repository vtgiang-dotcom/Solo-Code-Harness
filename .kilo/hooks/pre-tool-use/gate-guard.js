#!/usr/bin/env node
/**
 * gate-guard.js — PreToolUse hook for Solo-Code-Harness
 *
 * Validates shell commands with 7 category patterns + safe alternatives.
 * Upgraded from Claude Code version validate_bash.py.
 *
 * Categories:
 *   BLOCK (exit 2), WARN, PATH, MODE, SED, SEMANTIC, PIPE
 *
 * Exit codes: 0 = ALLOW, 2 = BLOCK
 *
 * Cross-platform tool name support:
 *   Claude Code: Bash | Kilo: bash | Gemini: run_command, execute
 *   Copilot: runCommand, terminal | Cursor: execute_command
 */

'use strict';

const MAX_STDIN = 1024 * 1024;

// ─── BLOCK PATTERNS (exit 2) ───────────────────────────────────────────────
const BLOCK_PATTERNS = [
  { name: 'rm_root', pattern: /rm\s+-rf?\s+\/(?:\s|$|\*|"|')/ },
  { name: 'rm_home', pattern: /rm\s+-rf?\s+~/ },
  { name: 'rm_wildcard', pattern: /rm\s+-rf?\s+\*/ },
  { name: 'rm_no_preserve', pattern: /rm\s+--no-preserve-root/ },
  { name: 'force_push_main', pattern: /git\s+push\s+.*(--force|-f)\s+.*(main|master)/ },
  { name: 'git_reset_hard', pattern: /git\s+reset\s+--hard/ },
  { name: 'drop_table', pattern: /DROP\s+(?:TABLE|DATABASE)/i },
  { name: 'truncate_table', pattern: /TRUNCATE\s+TABLE/i },
  { name: 'dd_raw', pattern: /dd\s+if=/ },
  { name: 'mkfs', pattern: /mkfs\./ },
  { name: 'shred', pattern: /shred\s+/ },
  { name: 'dev_write', pattern: />\s*\/dev\/sd[a-z]/ },
  { name: 'win_del_force', pattern: /del\s+\/f\s+\/s/ },
  { name: 'win_remove_recursive', pattern: /Remove-Item\s+.*-Recurse.*-Force/ },
  // Anchored to a real format invocation: `format` in command position with a
  // drive letter or /fs: switch. A bare /\bformat\s/ also matched
  // `--output-format json`, so the guard blocked ruff and grep -- and a guard
  // that blocks routine tooling teaches people to work around it.
  { name: 'format_disk', pattern: /(?:^|[;&|]\s*)format\s+(?:\/\S+\s+)*[a-zA-Z]:/i },
  { name: 'diskpart', pattern: /\bdiskpart\b/ },
  { name: 'shutdown_system', pattern: /(?:shutdown|reboot|halt)\b/ },
];

// ─── WARN PATTERNS ─────────────────────────────────────────────────────────
const WARN_PATTERNS = [
  { name: 'npm_global', pattern: /npm\s+install\s+-g/,
    message: 'npm install -g: global install — prefer local or npx' },
  { name: 'pip_solo', pattern: /pip\s+install\s+(?!-r|\.)/,
    message: 'pip install: consider adding to requirements.txt' },
  { name: 'curl_pipe_bash', pattern: /curl\s+.*\|\s*(?:ba)?sh/,
    message: 'curl | sh: piping to shell is unsafe. Review script first' },
  { name: 'eval_injection', pattern: /(?:eval|exec)\(.*\$/,
    message: 'eval/exec with variable input — code injection risk' },
  { name: 'debug_code', pattern: /console\.log\(|debugger;/,
    message: 'Debug code detected — remove before committing' },
];

// ─── PATH VALIDATION ───────────────────────────────────────────────────────
const PATH_WARN = [
  { name: 'tmp_volatile', pattern: /\b\/tmp\//,
    message: 'Writing to /tmp — data lost on reboot. Use persistent path.' },
  { name: 'tilde_expand', pattern: /\b~\//,
    message: 'Tilde ~ in script — may not expand as expected. Use $HOME.' },
  { name: 'deep_relative', pattern: /(?<!\w)\.\.\/\.\.\//,
    message: 'Deep relative path — fragile. Use absolute or project-relative.' },
];

// ─── MODE/PERMISSION VALIDATION ─────────────────────────────────────────────
const MODE_WARN = [
  { name: 'chmod_777', pattern: /chmod\s+.*777/,
    message: 'chmod 777 — world-writable. Use 755 or 644 instead.' },
  { name: 'chmod_plusx', pattern: /chmod\s+.*\+x\s+(?!.*\.sh)/,
    message: 'chmod +x on non-script file — verify intent.' },
];

// ─── SED/SYNTAX VALIDATION ─────────────────────────────────────────────────
const SED_WARN = [
  { name: 'piped_sed', pattern: /sed\s+.*\|.*sed/,
    message: 'Piped sed commands — fragile. Use single sed with -e.' },
  { name: 'sed_no_backup', pattern: /sed\s+-i\s+(?!.*\.bak)/,
    message: 'sed -i without .bak — no backup. Use sed -i.bak.' },
];

// ─── SEMANTIC VALIDATION ───────────────────────────────────────────────────
const SEMANTIC_WARN = [
  { name: 'kill_minus9', pattern: /kill\s+-9/,
    message: 'kill -9 is SIGKILL — no cleanup. Try kill -15 first.' },
  { name: 'docker_rm_force', pattern: /docker\s+rm\s+-f/,
    message: 'docker rm -f — force remove. May orphan resources.' },
  { name: 'npm_audit_force', pattern: /npm\s+audit\s+fix\s+--force/,
    message: 'npm audit fix --force — may break deps. Review first.' },
  { name: 'git_stash_drop', pattern: /git\s+stash\s+drop/,
    message: 'git stash drop — irreversible. Use git stash pop first.' },
];

// ─── PIPED DESTRUCTIVE ─────────────────────────────────────────────────────
const PIPE_DESTRUCTIVE = [
  { name: 'xargs_rm', pattern: /xargs\s+rm/,
    message: 'xargs rm — batch deletion. Review what xargs receives.' },
  { name: 'find_delete', pattern: /find\s+.*-delete/,
    message: 'find -delete — direct deletion. Use -print first to preview.' },
  { name: 'find_exec_rm', pattern: /find\s+.*-exec\s+rm/,
    message: 'find -exec rm — deletion via find. Use -print first to preview.' },
  { name: 'batch_branch_delete', pattern: /git\s+branch\s+.*\|.*xargs.*git\s+branch\s+-D/,
    message: 'Batch branch deletion — verify which branches will be deleted first.' },
  { name: 'kubectl_delete_all', pattern: /kubectl\s+delete\s+.*--all/,
    message: 'kubectl delete --all — deletes all resources in namespace.' },
];

// ─── SAFE ALTERNATIVES ─────────────────────────────────────────────────────
const SAFE_ALTERNATIVES = [
  { cmd: 'rm -rf', alt: 'mv <path> /tmp/<name>-backup first, then rm after verifying' },
  { cmd: 'rm ',    alt: 'Use mv to trash or add .bak suffix before deleting' },
  { cmd: 'git reset --hard', alt: 'Use git stash + git reset --soft to preserve changes' },
  { cmd: 'git push --force', alt: 'Use git push --force-with-lease to avoid overwriting' },
  { cmd: 'git branch -D', alt: 'Use git branch -d (lowercase) for merged branches only' },
  { cmd: 'docker rm -f', alt: 'Use docker stop first, then docker rm' },
  { cmd: 'kill -9', alt: 'Use kill -15 (SIGTERM) first for clean shutdown' },
];

// ─── Helpers ────────────────────────────────────────────────────────────────

function checkPatterns(patterns, command) {
  for (const { name, pattern, message } of patterns) {
    try {
      if (pattern.test(command)) {
        return { name, message: message || name };
      }
    } catch {}
  }
  return null;
}

function checkAlternatives(command) {
  return SAFE_ALTERNATIVES
    .filter(({ cmd }) => command.includes(cmd))
    .map(({ cmd, alt }) => `  ${cmd} → ${alt}`);
}

function isSensitivePath(filePath) {
  const sensitive = [/\.env(?:\.\w+)?$/i, /credentials\./i, /secrets?\./i, /\.pem$/i, /\.key$/i, /id_rsa/];
  return sensitive.some(p => p.test(filePath));
}

// ─── Main ───────────────────────────────────────────────────────────────────
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
    process.stderr.write('[GateGuard] Input truncated (>1MB) — allowing, cannot inspect\n');
    process.exit(0);
  }

  let input;
  try { input = JSON.parse(raw); } catch { process.exit(0); }

  // Cross-platform shell tool names
  const SHELL_TOOLS = new Set([
    'Bash', 'bash',           // Claude Code, Kilo
    'run_command', 'execute', // Gemini/Antigravity
    'runCommand', 'terminal', // Copilot
    'execute_command', 'shell', 'RunCommand', // Cursor, generic
  ]);

  const toolName = input.tool_name || '';
  const toolInput = input.tool_input || {};

  if (SHELL_TOOLS.has(toolName)) {
    const command = toolInput.command || toolInput.CommandLine || toolInput.cmd || toolInput.commandLine || '';

    // 1. BLOCK destructive patterns
    const blocked = checkPatterns(BLOCK_PATTERNS, command);
    if (blocked) {
      const alts = checkAlternatives(command);
      process.stderr.write(
        `\n[GateGuard] BLOCKED: ${blocked.message}\n` +
        `  Command: ${command.substring(0, 200)}\n` +
        (alts.length > 0 ? `  Safer alternatives:\n${alts.join('\n')}\n` : '') +
        `  Bypass: GATE_GUARD_BYPASS=1\n\n`
      );
      process.exit(2);
    }

    // 2-7. WARN categories
    const categories = [
      { label: 'WARNING', patterns: WARN_PATTERNS },
      { label: 'PATH', patterns: PATH_WARN },
      { label: 'MODE', patterns: MODE_WARN },
      { label: 'SED', patterns: SED_WARN },
      { label: 'SEMANTIC', patterns: SEMANTIC_WARN },
      { label: 'DESTRUCTIVE_PIPE', patterns: PIPE_DESTRUCTIVE },
    ];

    for (const { label, patterns } of categories) {
      const hit = checkPatterns(patterns, command);
      if (hit) {
        process.stderr.write(`[GateGuard] ${label}: ${hit.message}\n`);
      }
    }

    // Safe alternatives for non-blocking destructive commands
    const alts = checkAlternatives(command);
    for (const a of alts) {
      process.stderr.write(`[GateGuard] SAFE_ALT: ${a}\n`);
    }
  }

  // Sensitive file writes
  const filePath = toolInput.file_path || toolInput.path || toolInput.TargetFile || toolInput.AbsolutePath || toolInput.DirectoryPath || toolInput.uri || '';
  if (filePath && isSensitivePath(filePath)) {
    process.stderr.write(
      `[GateGuard] WARNING: Writing to sensitive file: ${filePath}\n` +
      `  Ensure no secrets are being committed.\n`
    );
  }

  process.exit(0);
});
