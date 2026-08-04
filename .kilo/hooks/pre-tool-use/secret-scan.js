#!/usr/bin/env node
/**
 * secret-scan.js — PreToolUse hook for Solo-Code-Harness
 *
 * Scans file content for hardcoded secrets before they're written.
 * Ported from ECC's governance-capture.js secret detection patterns.
 *
 * Exit codes:
 *   0 = ALLOW (no secrets found, or ignore)
 *   2 = BLOCK (secrets detected)
 */

'use strict';

const MAX_STDIN = 1024 * 1024;

// Secret detection patterns
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
  // Prefixed-token formats. `generic_api_key` only fires on a QUOTED value, so
  // bare `KEY=sk-ant-...` shell/env forms passed straight through -- this
  // project's own Anthropic key format included. Length floors sit above
  // doc-placeholder length so README examples do not trip the gate.
  // Pinned by tools/test_secret_patterns.py.
  { name: 'anthropic_key', pattern: /sk-ant-[A-Za-z0-9\-_]{24,}/ },
  { name: 'openai_project_key', pattern: /sk-proj-[A-Za-z0-9\-_]{20,}/ },
  { name: 'npm_token', pattern: /npm_[A-Za-z0-9]{36}/ },
  { name: 'gitlab_pat', pattern: /glpat-[A-Za-z0-9\-_]{20,}/ },
  { name: 'digitalocean_token', pattern: /dop_v1_[A-Za-z0-9]{64}/ },
  // Authorization header form: no quotes, no "=", so `hardcoded_token` missed it.
  { name: 'bearer_header', pattern: /Bearer\s+[A-Za-z0-9._\-+/=]{20,}/ },
];

// File extensions that commonly contain secrets
const SECRET_PRONE_EXTENSIONS = new Set([
  '.env', '.env.local', '.env.development', '.env.production',
  '.yml', '.yaml', '.json', '.ini', '.cfg', '.conf',
  '.pem', '.key', '.crt', '.cert', '.p12', '.pfx', '.jks',
  '.p8', '.ppk',
]);

/**
 * Scan content for secrets.
 * @param {string} content
 * @param {string} filePath
 * @returns {Array<{name: string, line: number}>}
 */
function scanSecrets(content, filePath) {
  if (!content || typeof content !== 'string') return [];

  const findings = [];
  const lines = content.split('\n');

  for (const { name, pattern } of SECRET_PATTERNS) {
    // Reset lastIndex for global regex
    const re = new RegExp(pattern.source, pattern.flags);
    for (let i = 0; i < lines.length; i++) {
      if (re.test(lines[i])) {
        findings.push({ name, line: i + 1 });
        re.lastIndex = 0; // reset after test
      }
    }
  }

  return findings;
}

/**
 * Check if file extension is secret-prone.
 * @param {string} filePath
 * @returns {boolean}
 */
function isSecretProneExtension(filePath) {
  if (!filePath) return false;
  const ext = '.' + filePath.split('.').pop().toLowerCase();
  return SECRET_PRONE_EXTENSIONS.has(ext);
}

/**
 * Check if path is in an excluded directory.
 */
function isExcludedPath(filePath) {
  if (!filePath) return true;
  const excluded = ['node_modules', '.venv', 'venv', '__pycache__', '.git', 'dist', 'build', '.next', '.cache'];
  return excluded.some(dir => filePath.includes(`/${dir}/`) || filePath.includes(`\\${dir}\\`));
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
    process.stderr.write('[SecretScan] Input truncated, skipping scan\n');
    process.exit(0);
  }

  let input;
  try {
    input = JSON.parse(raw);
  } catch {
    process.exit(0);
  }

  const toolInput = input.tool_input || {};
  const filePath = toolInput.file_path || toolInput.path || toolInput.TargetFile || toolInput.AbsolutePath || toolInput.DirectoryPath || toolInput.uri || '';
  const content = toolInput.content || toolInput.new_str || toolInput.text || toolInput.CodeContent || toolInput.ReplacementContent || (toolInput.ReplacementChunks ? JSON.stringify(toolInput.ReplacementChunks) : '') || '';

  // Skip excluded paths
  if (isExcludedPath(filePath)) {
    process.exit(0);
  }

  // Only scan secret-prone file types thoroughly
  // For other files, do a lightweight pass
  const findings = scanSecrets(content, filePath);
  const isProne = isSecretProneExtension(filePath);

  if (findings.length > 0) {
    if (isProne) {
      process.stderr.write(
        `\n[SecretScan] BLOCKED — potential secrets detected in ${filePath}:\n` +
        findings.map(f => `  Line ${f.line}: ${f.name}`).join('\n') +
        `\n  Remove hardcoded secrets and use environment variables instead.\n\n`
      );
      process.exit(2);
    } else {
      process.stderr.write(
        `[SecretScan] WARNING — potential secrets detected in ${filePath}:\n` +
        findings.map(f => `  Line ${f.line}: ${f.name}`).join('\n') +
        `\n  Verify this is not a real secret.\n`
      );
    }
  }

  process.exit(0);
});
