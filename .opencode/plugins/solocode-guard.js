/**
 * solocode-guard.js — OpenCode guard plugin (v2.5)
 *
 * Ported from Solo-Code Kilo hooks:
 *   .kilo/hooks/pre-tool-use/gate-guard.js
 *   .kilo/hooks/pre-tool-use/secret-scan.js
 *   .kilo/hooks/pre-tool-use/config-protection.js
 *
 * v2.5 CHANGES:
 *   - Added chat.message hook: auto-injects session state (handoff +
 *     feature list) on first message. No more "/remember" needed.
 *
 * v2.4 CHANGES:
 *   - Added temp-dir destruction patterns: rm_temp_linux (/tmp),
 *     rm_temp_win ($TEMP), del_temp_win ($TEMP).
 *
 * v2.3 CHANGES:
 *   - Added tool.execute.after hook: scans bash output for leaked secrets.
 *     Catches secrets that appear in command output (e.g., cat .env).
 *
 * v2.2 CHANGES:
 *   - Added chmod_chown_system pattern (chmod/chown -R on core system dirs).
 *   - Fixed extractPatchFilePaths: removed dead +++ unified-diff regex,
 *     added *** Move to: support. Verified against apply_patch.ts source.
 *   - normalizeCommand already implemented in v2.1 (verified working).
 *
 * v2.1 CHANGES:
 *   - Added 12 new BLOCK_PATTERNS covering orphan destructive commands
 *     (v2.1-orphan-plan.md): rm_relative_wildcard, rm_r_wildcard,
 *     rm_r_f_wildcard, git_clean_force, rm_system_dir, curl_pipe_shell,
 *     dd_device_write, win_rd_recursive, win_del_any, win_format_volume,
 *     win_stop_computer, win_restart_computer.
 *
 * KNOWN GAPS (v2.2):
 *   (a) Fork bomb :(){ :|:& };: — hiếm khi model tự sinh, dễ false.
 *   (b) Obfuscated commands (base64, eval chains, variable indirection).
 */

import fs from 'fs';

// ─── Destructive Command Patterns ──────────────────────────────────────────
// Source: gate-guard.js:24-41

const BLOCK_PATTERNS = [
  // ── v1 patterns (port from gate-guard.js:24-41) ─────────────────────
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
  { name: 'format_disk', pattern: /\bformat\s/ },
  { name: 'diskpart', pattern: /\bdiskpart\b/ },
  { name: 'shutdown_system', pattern: /(?:shutdown|reboot|halt)\b/ },
  // ── v2.1 patterns: orphan rm variants (opencode.json:11,13,14) ─────
  // v2.1: rm -rf ./* — thư mục con của thư mục hiện tại
  { name: 'rm_relative_wildcard', pattern: /rm\s+-rf?\s+\.\// },
  // v2.1: rm -r * — recursive wildcard (không -f)
  { name: 'rm_r_wildcard', pattern: /rm\s+-r\s+\*/ },
  // v2.1: rm -r -f * — flag tách rời
  { name: 'rm_r_f_wildcard', pattern: /rm\s+-r\s+-f\s+\*/ },
  // ── v2.1: git clean force (opencode.json:20-22) ─────────────────────
  { name: 'git_clean_force', pattern: /git\s+clean\s+-f/ },
  // ── v2.1: rm thư mục hệ thống (logic mới, user duyệt) ──────────────
  // Bắt rm -rf vào thư mục hệ thống cốt lõi: /etc /usr /var /bin /lib
  // /boot /sbin /lib64 /opt /root /sys /proc /dev
  { name: 'rm_system_dir', pattern: /rm\s+-rf?\s+\/(?:etc|usr|var|bin|lib(?:64)?|boot|sbin|opt|root|sys|proc|dev)(?:\/|\s|$)/ },
  // ── v2.1: curl|sh / wget|bash (nâng từ WARN gate-guard.js:49 lên BLOCK) ─
  { name: 'curl_pipe_shell', pattern: /(?:curl|wget)\s+.*\|\s*(?:ba)?sh\b/ },
  // ── v2.1: dd of=/dev/* (mở rộng dd_raw) ─────────────────────────────
  { name: 'dd_device_write', pattern: /dd\s+.*of=\/dev\// },
  // ── v2.2: chmod/chown -R trên thư mục hệ thống cốt lõi ─────────────
  // Bắt chmod/chown -R vào: /etc /usr /var /bin /lib /boot /sbin /lib64
  // /opt /root /sys /proc /dev (cùng danh sách rm_system_dir)
  { name: 'chmod_chown_system', pattern: /(?:chmod|chown)\s+-R\s+(?:[^\/\s]+\s+)*\/(?:etc|usr|var|bin|lib(?:64)?|boot|sbin|opt|root|sys|proc|dev)(?:\/|\s|$)/ },
  // ── v2.4: temp-dir destruction patterns ───────────────────────────
  // Bắt rm -rf /tmp/* (Linux temp directory — cached data, sockets)
  { name: 'rm_temp_linux', pattern: /rm\s+-rf?\s+\/tmp\// },
  // Bắt rm -rf $TEMP\* hoặc $env:TEMP\* (Windows temp directory)
  { name: 'rm_temp_win', pattern: /rm\s+-rf?\s+\$?(?:env:)?TEMP\b/i },
  // Bắt del /q hoặc /s $TEMP\* (Windows temp file deletion)
  { name: 'del_temp_win', pattern: /del\s+(?:\/f\s+)?\/[qs]\s+\$?(?:env:)?TEMP\b/i },
  // ── v2.1: Windows patterns (opencode.json:39,40-42,43,45,46,47) ────
  // rd /s hoặc rmdir /s (bắt /s flag đứng sau space — tránh false
  // positive với path chứa "src" như C:/src/)
  // v2.1: rd /s hoặc rmdir /s (flag có hoặc không space trước)
  { name: 'win_rd_recursive', pattern: /(?:rd|rmdir)\s+(?:.*\s)?\/s\b/i },
  // v2.1: del có ít nhất một flag /q /s /f (flag có hoặc không space trước)
  { name: 'win_del_any', pattern: /del\s+(?:.*\s)?\/[qsf]\b/i },
  // Format-Volume PowerShell
  { name: 'win_format_volume', pattern: /\bFormat-Volume\b/ },
  // Stop-Computer PowerShell
  { name: 'win_stop_computer', pattern: /\bStop-Computer\b/ },
  // Restart-Computer PowerShell
  { name: 'win_restart_computer', pattern: /\bRestart-Computer\b/ },
];

// ─── Secret Detection Patterns ─────────────────────────────────────────────
// Source: secret-scan.js:19-34

const SECRET_PATTERNS = [
  { name: 'aws_access_key', pattern: /(?:AKIA|ASIA)[A-Z0-9]{16}/ },
  { name: 'aws_secret_key', pattern: /(?:aws|amazon).{0,20}(?:secret|key|token).{0,10}[:=]\s*["'][A-Za-z0-9/+=]{20,}/i },
  { name: 'generic_api_key', pattern: /(?:api[_-]?key|apikey|secret|password)\s*[:=]\s*["'][^"']{8,}["']/i },
  { name: 'private_key_pem', pattern: /-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----/ },
  { name: 'jwt_token', pattern: /eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/ },
  { name: 'github_token', pattern: /(?:gh[pousr]_|github[_-]?pat[_-]?|github[_-]?token[_-]?)[A-Za-z0-9_]{20,}/i },
  { name: 'google_api_key', pattern: /AIza[0-9A-Za-z_-]{35}/ },
  { name: 'slack_token', pattern: /xox[baprs]-[0-9A-Za-z-]{10,}/ },
  { name: 'stripe_key', pattern: /(?:sk|pk)_(?:test|live)_[0-9a-zA-Z]{24,}/ },
  { name: 'mongodb_uri', pattern: /mongodb(?:\+srv)?:\/\/[^:]+:[^@]+@/ },
  { name: 'postgres_uri', pattern: /postgres(?:ql)?:\/\/[^:]+:[^@]+@/ },
  { name: 'redis_uri', pattern: /redis:\/\/[^:]+:[^@]+@/ },
  { name: 'hardcoded_token', pattern: /(?:token|bearer)\s*[:=]\s*["'][A-Za-z0-9._\-+/=]{20,}["']/i },
  { name: 'discord_webhook', pattern: /https:\/\/discord(?:app)?\.com\/api\/webhooks\/\d+\/[A-Za-z0-9_-]+/i },
  { name: 'basic_auth', pattern: /https?:\/\/[^:]+:[^@]+@/ },
];

// ─── Protected Config Files ────────────────────────────────────────────────
// Source: config-protection.js:21-45

const PROTECTED_FILES = new Set([
  '.eslintrc', '.eslintrc.js', '.eslintrc.cjs', '.eslintrc.json',
  '.eslintrc.yml', '.eslintrc.yaml',
  'eslint.config.js', 'eslint.config.mjs', 'eslint.config.cjs',
  'eslint.config.ts', 'eslint.config.mts', 'eslint.config.cts',
  '.prettierrc', '.prettierrc.js', '.prettierrc.cjs', '.prettierrc.json',
  '.prettierrc.yml', '.prettierrc.yaml',
  'prettier.config.js', 'prettier.config.cjs', 'prettier.config.mjs',
  'biome.json', 'biome.jsonc',
  '.ruff.toml', 'ruff.toml',
  '.shellcheckrc',
  '.stylelintrc', '.stylelintrc.json', '.stylelintrc.yml',
  '.markdownlint.json', '.markdownlint.yaml', '.markdownlintrc',
  '.flake8', '.pylintrc', 'tox.ini',
  '.golangci.yml', '.golangci.yaml', '.golangci.json',
  '.editorconfig',
]);

// ─── Excluded Directories (secret-scan) ────────────────────────────────────
// Source: secret-scan.js:86

const EXCLUDED_DIRS = ['node_modules', '.venv', 'venv', '__pycache__', '.git', 'dist', 'build', '.next', '.cache'];

// ─── Secret-Prone Extensions ───────────────────────────────────────────────
// Source: secret-scan.js:37-42

const SECRET_PRONE_EXTENSIONS = new Set([
  '.env', '.env.local', '.env.development', '.env.production',
  '.yml', '.yaml', '.json', '.ini', '.cfg', '.conf',
  '.pem', '.key', '.crt', '.cert', '.p12', '.pfx', '.jks',
  '.p8', '.ppk',
]);

// ═══════════════════════════════════════════════════════════════════════════
// Core Logic — Pure Functions
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Check if a shell command matches any destructive pattern.
 * @param {string} command
 * @returns {{ name: string } | null}
 */
function isDestructiveCommand(command) {
  if (!command || typeof command !== 'string') return null;
  for (const { name, pattern } of BLOCK_PATTERNS) {
    try {
      if (pattern.test(command)) return { name };
    } catch (_) {
      // Individual pattern failure — skip silently
    }
  }
  return null;
}

/**
 * v2: Normalize a shell command to defeat common bypasses.
 * LOGIC MỚI — không có trong bản gốc gate-guard.js.
 * Steps: collapse whitespace; strip sudo / env VAR=val / bash -c / sh -c
 * wrappers (repeatedly); strip absolute path of the first command to basename.
 * Does NOT lowercase (preserve case-sensitive paths on Linux).
 * @param {string} command
 * @returns {string}
 */
function normalizeCommand(command) {
  if (!command || typeof command !== 'string') return '';
  let cmd = command;

  // 1. Collapse all whitespace (incl. tabs) to single space, trim
  cmd = cmd.replace(/\s+/g, ' ').trim();

  // 2. Strip repeated prefix wrappers (sudo / env VAR=val / bash -c / sh -c)
  let prev;
  do {
    prev = cmd;
    cmd = cmd.replace(/^sudo\s+/, '');
    cmd = cmd.replace(/^env(\s+[\w]+=[^\s]*)+\s+/, '');
    cmd = cmd.replace(/^(?:bash|sh)\s+-c\s+/, '');
    cmd = cmd.replace(/^(['"])(.*)\1$/, '$2'); // strip surrounding quotes
  } while (cmd !== prev);

  // 3. Strip absolute path of first command to basename (/bin/dd -> dd)
  cmd = cmd.replace(/^\/?(?:[\w.-]+\/)+([\w.-]+)/, '$1');

  return cmd;
}

/**
 * Scan string content line-by-line for hardcoded secrets.
 * @param {string} content
 * @returns {Array<{ name: string, line: number }>}
 */
function scanSecrets(content) {
  if (!content || typeof content !== 'string') return [];
  const findings = [];
  const lines = content.split('\n');
  for (const { name, pattern } of SECRET_PATTERNS) {
    const re = new RegExp(pattern.source, pattern.flags);
    for (let i = 0; i < lines.length; i++) {
      try {
        if (re.test(lines[i])) {
          findings.push({ name, line: i + 1 });
          re.lastIndex = 0;
        }
      } catch (_) {
        // skip broken pattern on this line
      }
    }
  }
  return findings;
}

/**
 * Check if file path has a secret-prone extension.
 * @param {string} filePath
 * @returns {boolean}
 */
function isSecretProneExtension(filePath) {
  if (!filePath || typeof filePath !== 'string') return false;
  const parts = filePath.split('.');
  if (parts.length < 2) return false;
  const ext = '.' + parts.pop().toLowerCase();
  return SECRET_PRONE_EXTENSIONS.has(ext);
}

/**
 * Check if file path is in an excluded directory.
 * @param {string} filePath
 * @returns {boolean}
 */
function isExcludedPath(filePath) {
  if (!filePath || typeof filePath !== 'string') return false;
  const normalized = filePath.replace(/\\/g, '/');
  return EXCLUDED_DIRS.some(function (dir) {
    return normalized.indexOf('/' + dir + '/') !== -1;
  });
}

/**
 * Full secret check: scan content, apply exclusion filter only.
 * Always scans regardless of file extension (no isSecretProneExtension check).
 * When filePath is empty (apply_patch), scans raw content without exclusions.
 *
 * @param {string} content
 * @param {string} [filePath]
 * @returns {boolean}
 */
function containsSecret(content, filePath) {
  if (!content) return false;
  const findings = scanSecrets(content);
  if (findings.length === 0) return false;

  // Exclusion filter only — scan all file types (.js, .ts, .py, etc.)
  if (filePath) {
    if (isExcludedPath(filePath)) return false;
  }
  return true;
}

/**
 * Check if write targets a protected linter/formatter config that already exists.
 * Allows first-time creation (file doesn't exist yet).
 * @param {string} filePath
 * @returns {boolean}
 */
function weakensConfig(filePath) {
  if (!filePath || typeof filePath !== 'string') return false;
  var basename = filePath;
  var slash = basename.lastIndexOf('/');
  var backslash = basename.lastIndexOf('\\');
  basename = basename.substring(Math.max(slash, backslash) + 1);

  if (!PROTECTED_FILES.has(basename)) return false;

  // Block only if file already exists (modification, not first-time creation)
  try {
    fs.lstatSync(filePath);
    return true;
  } catch (_) {
    // ENOENT or any other error — fail open, allow the write
    return false;
  }
}

/**
 * v2.2: Extract file paths from apply_patch patchText.
 * VERIFIED against opencode-dev/packages/opencode/src/patch/index.ts:70-101.
 * Patch language uses *** Action File: headers (NOT unified diff).
 * Handles: Add File, Update File, Delete File, and Move to sub-header.
 * @param {string} patchText
 * @returns {string[]}
 */
function extractPatchFilePaths(patchText) {
  if (!patchText || typeof patchText !== 'string') return [];
  const paths = [];
  const lines = patchText.split('\n');
  for (const line of lines) {
    let m = line.match(/^\*\*\*\s+(?:Update|Add|Delete|Move to)\s+File:\s+(.+)$/);
    if (m) { paths.push(m[1].trim()); }
  }
  return paths;
}

// ═══════════════════════════════════════════════════════════════════════════
// v2.5: Session State Injection
// ═══════════════════════════════════════════════════════════════════════════

const stateInjectedSessions = new Set();

function readStateFile(dir, name) {
  try {
    const p = dir + '/.opencode/state/' + name;
    if (!fs.existsSync(p)) return null;
    return fs.readFileSync(p, 'utf-8').trim();
  } catch (_) { return null; }
}

// ═══════════════════════════════════════════════════════════════════════════
// OpenCode Plugin — Hook Registration (ES module export)
// Signature: https://opencode.ai/docs/plugins/
// ═══════════════════════════════════════════════════════════════════════════

export const SoloCodeGuard = async ({ project, client, $, directory, worktree }) => {
  return {
    // v2.5: Auto-inject session state on first message
    'chat.message': async (input, output) => {
      try {
        const sid = input.sessionID;
        if (!sid || stateInjectedSessions.has(sid)) return;
        stateInjectedSessions.add(sid);

        const handoff = readStateFile(directory, 'session-handoff.md');
        const features = readStateFile(directory, 'feature_list.json');

        if (!handoff && !features) return;

        let text = '[SoloCode] Current project state:\n\n';
        if (handoff) text += '### Session Handoff\n' + handoff + '\n\n';
        if (features) {
          try {
            const list = JSON.parse(features);
            const active = list.filter(function(f) { return f.status === 'in-progress'; });
            const pending = list.filter(function(f) { return f.status === 'not-started'; });
            text += '### Feature Status\n';
            text += '- In progress: ' + (active.length || 'none') + '\n';
            text += '- Pending: ' + pending.length + '\n';
            if (active.length) text += '- Active: ' + active.map(function(f) { return f.name; }).join(', ') + '\n';
          } catch (_) { text += features.substring(0, 200) + '\n'; }
        }
        output.parts.push({ text: text });
      } catch (_) { /* fail open */ }
    },
    'tool.execute.before': async (input, output) => {
      try {
        const tool = input.tool;
        const args = output.args || {};
        switch (tool) {
          case 'bash': {
            const raw = args.command || '';
            // v2: check BOTH the raw command AND the normalized command
            const hit = isDestructiveCommand(raw) || isDestructiveCommand(normalizeCommand(raw));
            if (hit) throw new Error('[SoloCode] Blocked destructive command: ' + hit.name);
            break;
          }
          case 'write': {
            if (containsSecret(args.content || '', args.filePath)) throw new Error('[SoloCode] Secret detected, write blocked');
            if (weakensConfig(args.filePath)) throw new Error('[SoloCode] Config weakening blocked');
            break;
          }
          case 'edit': {
            const combined = (args.oldString || '') + '\n' + (args.newString || '');
            if (containsSecret(combined, args.filePath)) throw new Error('[SoloCode] Secret detected, edit blocked');
            if (weakensConfig(args.filePath)) throw new Error('[SoloCode] Config weakening blocked');
            break;
          }
          case 'apply_patch': {
            const patchText = args.patchText || '';
            if (containsSecret(patchText, '')) throw new Error('[SoloCode] Secret detected, apply_patch blocked');
            // v2: parse file paths from patch and run config-protection
            for (const fp of extractPatchFilePaths(patchText)) {
              if (weakensConfig(fp)) throw new Error('[SoloCode] Config weakening blocked (apply_patch): ' + fp);
            }
            break;
          }
        }
      } catch (err) {
        if (err instanceof Error && err.message && err.message.indexOf('[SoloCode]') === 0) throw err;
        // fail open: swallow all other runtime errors
      }
    },
    // v2.2: Post-execution hook — scan bash output for leaked secrets
    'tool.execute.after': async (input, output) => {
      try {
        if (input.tool !== 'bash') return;
        const out = output.output || '';
        if (typeof out !== 'string' || out.length === 0) return;
        const findings = scanSecrets(out);
        if (findings.length > 0) {
          const names = findings.map(function (f) { return f.name + ':' + f.line; }).join(', ');
          throw new Error('[SoloCode] Secret leaked in bash output: ' + names);
        }
      } catch (err) {
        if (err instanceof Error && err.message && err.message.indexOf('[SoloCode]') === 0) throw err;
        // fail open
      }
    }
  };
};

// ═══════════════════════════════════════════════════════════════════════════
// Pattern Provenance Table
// ── Mỗi pattern/logic ↔ nguồn gốc (file:dòng) hoặc đánh dấu v2-MỚI ──
// ═══════════════════════════════════════════════════════════════════════════
//
// ## isDestructiveCommand — BLOCK_PATTERNS
//   rm_root           → gate-guard.js:24
//   rm_home           → gate-guard.js:25
//   rm_wildcard       → gate-guard.js:26
//   rm_no_preserve    → gate-guard.js:27
//   force_push_main   → gate-guard.js:28
//   git_reset_hard    → gate-guard.js:29
//   drop_table        → gate-guard.js:30
//   truncate_table    → gate-guard.js:31
//   dd_raw            → gate-guard.js:32
//   mkfs              → gate-guard.js:33
//   shred             → gate-guard.js:34
//   dev_write         → gate-guard.js:35
//   win_del_force     → gate-guard.js:36
//   win_remove_recursive → gate-guard.js:37
//   format_disk       → gate-guard.js:38
//   diskpart          → gate-guard.js:39
//   shutdown_system   → gate-guard.js:40
//
// ## containsSecret — SECRET_PATTERNS
//   aws_access_key    → secret-scan.js:19
//   aws_secret_key    → secret-scan.js:20
//   generic_api_key   → secret-scan.js:21
//   private_key_pem   → secret-scan.js:22
//   jwt_token         → secret-scan.js:23
//   github_token      → secret-scan.js:24
//   google_api_key    → secret-scan.js:25
//   slack_token       → secret-scan.js:26
//   stripe_key        → secret-scan.js:27
//   mongodb_uri       → secret-scan.js:28
//   postgres_uri      → secret-scan.js:29
//   redis_uri         → secret-scan.js:30
//   hardcoded_token   → secret-scan.js:31
//   discord_webhook   → secret-scan.js:32
//   basic_auth        → secret-scan.js:33
//
// ## containsSecret — helper functions
//   scanSecrets()         → secret-scan.js:50-68
//   isSecretProneExt()    → secret-scan.js:75-79 (SECRET_PRONE_EXTENSIONS:37-42)
//   isExcludedPath()      → secret-scan.js:84-88 (excluded dirs:86)
//
// ## weakensConfig — PROTECTED_FILES
//   ESLint files          → config-protection.js:22-26
//   Prettier files        → config-protection.js:28-30
//   Biome files           → config-protection.js:32
//   Ruff files            → config-protection.js:34
//   ShellCheck            → config-protection.js:36
//   Stylelint files       → config-protection.js:37
//   Markdownlint files    → config-protection.js:38
//   Python files          → config-protection.js:40
//   Go files              → config-protection.js:42
//   EditorConfig          → config-protection.js:44
//   Exists-check logic    → config-protection.js:94-107
//
// ## v2.4 additions (BLOCK_PATTERNS + test coverage)
//   rm_temp_linux       → v2.4-NEW (rm -rf /tmp/* — cached data, sockets)
//   rm_temp_win         → v2.4-NEW (rm -rf $TEMP\* — Windows temp dir)
//   del_temp_win        → v2.4-NEW (del /q $TEMP\* — Windows temp file del)
//
// ## v2.3 additions (hook expansion)
//   tool.execute.after  → v2.3-NEW (scan bash output for leaked secrets)
//
// ## v2.2 additions (BLOCK_PATTERNS + extractPatchFilePaths fix)
//   chmod_chown_system   → v2.2-NEW (user-approved: chmod/chown -R on system dirs)
//                         (cùng danh sách thư mục với rm_system_dir)
//   extractPatchFilePaths → v2.2-FIXED (verified against patch/index.ts:70-101,
//                            removed dead +++ unified-diff regex, added Move to:)
//
// ## v2.1 additions (BLOCK_PATTERNS)
//   rm_relative_wildcard → opencode.json:11 (v2.1-orphan-plan.md)
//   rm_r_wildcard        → opencode.json:13
//   rm_r_f_wildcard      → opencode.json:14
//   git_clean_force      → opencode.json:20-22
//   rm_system_dir        → v2.1-NEW (logic mới có chủ đích, user duyệt)
//                         (vá gap rm_root: /etc /usr /var /bin /lib /boot /sbin
//                          /lib64 /opt /root /sys /proc /dev)
//   curl_pipe_shell      → nâng từ WARN (gate-guard.js:49) lên BLOCK, user duyệt
//   dd_device_write      → mở rộng dd_raw (opencode.json:32 + user duyệt)
//   win_rd_recursive     → opencode.json:39,43
//   win_del_any          → opencode.json:40-42 (mở rộng win_del_force)
//   win_format_volume    → opencode.json:45
//   win_stop_computer    → opencode.json:46
//   win_restart_computer → opencode.json:47
//
// ## v2 — LOGIC MỚI (không có trong bản gốc)
//   normalizeCommand()       → v2-NEW (chống sudo/env/bash -c/whitespace/abs-path)
//   extractPatchFilePaths()  → v2-NEW (CẦN KIỂM SOURCE: apply_patch.ts hunk format)
//
// ## Normalize command
//   v1: KHÔNG TÌM THẤY TRONG BẢN GỐC → v2: đã bổ sung (logic mới).
//
// ## KNOWN GAPS (patterns intentionally not added)
//   fork bomb :(){ :|:& };:   → hiếm, dễ false negative, ghi nhận
//   Obfuscated commands       → base64, eval chains, variable indirection
//
// ## MCP TOOL PERMISSION FLOW (verified 2026-06-22)
//   Source: opencode-dev/packages/opencode/src/session/tools.ts:128-150
//   - MCP tools DO pass through tool.execute.before/after hooks
//   - MCP tool names are namespaced: <server>_<tool> (mcp/index.ts:646)
//   - MCP tools are subject to opencode.json permission (* wildcard → ask)
//   - Current MCP servers (context7, playwright) are safe:
//     context7 = read-only docs lookup, playwright = disabled
//   - Risk: if future MCP server has write/bash capability, guard plugin
//     should inspect output.args for destructive patterns (not just bash tool)
