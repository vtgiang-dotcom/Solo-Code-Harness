#!/usr/bin/env node
/**
 * run-with-flags.js — Hook dispatcher utility for Solo-Code-Harness
 *
 * Routes hook execution through profile flags (minimal, standard, strict).
 * Simplified port of ECC's run-with-flags.js.
 *
 * Usage: node run-with-flags.js <event-id> <target-script> [profile]
 *   Profiles: minimal, standard, strict
 *   Reads input from stdin, writes output to stdout
 */

'use strict';

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const DEFAULT_PROFILE = 'standard';
const ALLOWED_PROFILES = new Set(['minimal', 'standard', 'strict']);

function main() {
  const [, , eventId, targetScript, profileArg] = process.argv;
  const raw = fs.readFileSync(0, 'utf8');

  const profile = ALLOWED_PROFILES.has(profileArg) ? profileArg : DEFAULT_PROFILE;

  // Read hook profile config
  let hookConfig = {};
  try {
    const configPath = path.join(process.cwd(), '.kilo', 'hooks', 'hooks.json');
    if (fs.existsSync(configPath)) {
      hookConfig = JSON.parse(fs.readFileSync(configPath, 'utf8'));
    }
  } catch {
    // Use defaults
  }

  // Check if this hook is enabled for current profile
  const enabledHooks = hookConfig.profiles?.[profile] || [];
  if (enabledHooks.length > 0 && !enabledHooks.includes(eventId)) {
    // Hook not in current profile, pass through
    process.stdout.write(raw);
    process.exit(0);
  }

  if (!targetScript) {
    process.stdout.write(raw);
    process.exit(0);
  }

  const scriptPath = path.resolve(targetScript);
  if (!fs.existsSync(scriptPath)) {
    process.stderr.write(`[RunWithFlags] Script not found: ${targetScript}\n`);
    process.stdout.write(raw);
    process.exit(0);
  }

  const result = spawnSync(process.execPath, [scriptPath], {
    input: raw,
    encoding: 'utf8',
    env: { ...process.env, HOOK_EVENT_NAME: eventId, HOOK_PROFILE: profile },
    cwd: process.cwd(),
    timeout: 30000,
    windowsHide: true,
  });

  const stdout = typeof result.stdout === 'string' ? result.stdout : '';
  if (stdout) {
    process.stdout.write(stdout);
  } else {
    process.stdout.write(raw);
  }

  if (result.stderr) {
    process.stderr.write(result.stderr);
  }

  if (result.error || result.status === null || result.signal) {
    process.exit(0); // Non-blocking on error
  }

  process.exit(Number.isInteger(result.status) ? result.status : 0);
}

main();
