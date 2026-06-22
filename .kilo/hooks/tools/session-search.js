#!/usr/bin/env node
/**
 * session-search.js — Cross-session full-text search tool
 *
 * Searches across session logs, tool logs, and learning databases
 * for past conversations, errors, and patterns.
 *
 * Sources searched:
 *   .kilo/state/sessions/        — Session metadata files
 *   .kilo/state/tool-outputs/    — Saved large tool outputs
 *   ~/.kilo/learnings/tool-log.jsonl  — Global tool execution log
 *   ~/.kilo/learnings/learnings.json  — Global learning database
 *   .kilo/learnings/db/learnings.json — Local learning database
 *
 * Usage:
 *   node .kilo/hooks/tools/session-search.js <query> [--limit=20] [--source=sessions|tools|learnings|all] [--json]
 *
 * Exit codes: 0 (found results), 1 (no results), 2 (error)
 */

'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

// ─── Configuration ──────────────────────────────────────────────────────────
const GLOBAL_DIR = path.join(os.homedir(), '.kilo', 'learnings');
const LOCAL_DIR = path.join(process.cwd(), '.kilo');
const SESSIONS_DIR = path.join(LOCAL_DIR, 'state', 'sessions');
const TOOL_OUTPUTS_DIR = path.join(LOCAL_DIR, 'state', 'tool-outputs');
const TOOL_LOG_FILE = path.join(GLOBAL_DIR, 'tool-log.jsonl');
const GLOBAL_DB = path.join(GLOBAL_DIR, 'learnings.json');
const LOCAL_DB = path.join(LOCAL_DIR, 'learnings', 'db', 'learnings.json');

const MAX_RESULTS = 50;

// ─── CLI Parsing ────────────────────────────────────────────────────────────

function parseArgs(argv) {
  const args = { query: '', limit: 20, source: 'all', json: false };
  for (const arg of argv) {
    if (arg.startsWith('--limit=')) {
      args.limit = Math.min(parseInt(arg.split('=')[1], 10) || 20, MAX_RESULTS);
    } else if (arg.startsWith('--source=')) {
      args.source = arg.split('=')[1];
    } else if (arg === '--json') {
      args.json = true;
    } else if (!arg.startsWith('--')) {
      args.query += (args.query ? ' ' : '') + arg;
    }
  }
  return args;
}

function usage() {
  process.stderr.write(
    'Usage: node session-search.js <query> [--limit=20] [--source=sessions|tools|learnings|all] [--json]\n\n' +
    'Sources:\n' +
    '  sessions   — .kilo/state/sessions/*.json\n' +
    '  tools      — .kilo/state/tool-outputs/*.txt + tool-log.jsonl\n' +
    '  learnings  — ~/.kilo/learnings/learnings.json + .kilo/learnings/db/learnings.json\n' +
    '  all        — all of the above (default)\n\n' +
    'Use --json for machine-readable output.\n'
  );
}

// ─── Search Helpers ─────────────────────────────────────────────────────────

function readJSON(filePath, fallback) {
  try {
    if (fs.existsSync(filePath)) return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch {}
  return fallback;
}

function readJSONL(filePath, limit) {
  if (!fs.existsSync(filePath)) return [];
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const lines = content.trim().split('\n').filter(Boolean);
    return lines.slice(-Math.min(lines.length, limit)).map(l => {
      try { return JSON.parse(l); } catch { return null; }
    }).filter(Boolean);
  } catch {
    return [];
  }
}

function matchScore(text, query) {
  if (!text || !query) return 0;
  const lowerText = text.toLowerCase();
  const lowerQuery = query.toLowerCase();
  const terms = lowerQuery.split(/\s+/).filter(t => t.length > 0);

  if (terms.length === 0) return 0;

  // Exact phrase match gets highest score
  if (lowerText.includes(lowerQuery)) return Math.max(...terms.map(t => 0.5));

  // Score by how many terms match
  let score = 0;
  for (const term of terms) {
    const regex = new RegExp(term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
    const matches = lowerText.match(regex);
    if (matches) score += matches.length * 0.5;
  }
  return score;
}

// ─── Source Searchers ───────────────────────────────────────────────────────

function searchSessions(query, limit) {
  const results = [];
  if (!fs.existsSync(SESSIONS_DIR)) return results;

  const files = fs.readdirSync(SESSIONS_DIR).filter(f => f.endsWith('.json'));
  for (const file of files) {
    const filePath = path.join(SESSIONS_DIR, file);
    const data = readJSON(filePath, null);
    if (!data) continue;

    const searchable = JSON.stringify(data);
    const score = matchScore(searchable, query);
    if (score === 0) continue;

    results.push({
      source: 'sessions',
      file: file,
      sessionId: data.sessionId || file.replace('.json', ''),
      branch: data.branch || 'unknown',
      startedAt: data.startedAt || '',
      sha: data.sha || '',
      relevance: Math.round(score * 100) / 100,
      summary: JSON.stringify(data).substring(0, 200),
    });
  }

  results.sort((a, b) => b.relevance - a.relevance);
  return results.slice(0, limit);
}

function searchToolOutputs(query, limit) {
  const results = [];
  if (!fs.existsSync(TOOL_OUTPUTS_DIR)) return results;

  const files = fs.readdirSync(TOOL_OUTPUTS_DIR).filter(f => f.endsWith('.txt'));
  for (const file of files) {
    const filePath = path.join(TOOL_OUTPUTS_DIR, file);
    try {
      const content = fs.readFileSync(filePath, 'utf8');
      const score = matchScore(content.substring(0, 5000), query);
      if (score === 0) continue;

      // Extract relevant context (first occurrence)
      const idx = content.toLowerCase().indexOf(query.toLowerCase());
      const excerpt = idx >= 0
        ? content.substring(Math.max(0, idx - 40), idx + query.length + 120).replace(/\n/g, '↵')
        : content.substring(0, 200);

      results.push({
        source: 'tool-outputs',
        file: file,
        relevance: Math.round(score * 100) / 100,
        excerpt,
      });
    } catch {}
  }

  results.sort((a, b) => b.relevance - a.relevance);
  return results.slice(0, limit);
}

function searchToolLog(query, limit) {
  const results = [];
  const entries = readJSONL(TOOL_LOG_FILE, 2000);

  for (const entry of entries) {
    if (!entry) continue;
    const searchable = JSON.stringify(entry);
    const score = matchScore(searchable, query);
    if (score === 0) continue;

    results.push({
      source: 'tool-log',
      ts: entry.ts || '',
      tool: entry.tool || '',
      chars: entry.chars || 0,
      tokens: entry.tokens || 0,
      relevance: Math.round(score * 100) / 100,
    });
  }

  results.sort((a, b) => b.relevance - a.relevance);
  return results.slice(0, limit);
}

function searchLearnings(query, limit) {
  const results = [];

  // Global learnings
  const globalEntries = readJSON(GLOBAL_DB, []);
  for (const entry of globalEntries) {
    const searchable = `${entry.scope} ${entry.category} ${entry.content}`;
    const score = matchScore(searchable, query);
    if (score === 0) continue;

    results.push({
      source: 'learnings-global',
      id: entry.id || '',
      scope: entry.scope,
      category: entry.category,
      content: entry.content,
      hit_count: entry.hit_count || 1,
      last_seen: entry.last_seen || '',
      relevance: Math.round(score * 100) / 100,
    });
  }

  // Local (project) learnings
  const localEntries = readJSON(LOCAL_DB, []);
  for (const entry of localEntries) {
    const searchable = `${entry.scope} ${entry.category} ${entry.content}`;
    const score = matchScore(searchable, query);
    if (score === 0) continue;

    results.push({
      source: 'learnings-local',
      id: entry.id || '',
      scope: entry.scope,
      category: entry.category,
      content: entry.content,
      hit_count: entry.hit_count || 1,
      last_seen: entry.last_seen || '',
      relevance: Math.round(score * 100) / 100,
    });
  }

  results.sort((a, b) => b.relevance - a.relevance);
  return results.slice(0, limit);
}

// ─── Output Formatters ──────────────────────────────────────────────────────

function formatText(results, query) {
  const lines = [];
  lines.push(`\n🔍 Session Search: "${query}" — ${results.length} result(s)`);
  lines.push('═'.repeat(80));

  let lastSource = '';
  for (const r of results) {
    if (r.source !== lastSource) {
      const labels = {
        'sessions': '📁 Session Logs',
        'tool-outputs': '📄 Tool Outputs',
        'tool-log': '📊 Tool Execution Log',
        'learnings-global': '🧠 Global Learnings',
        'learnings-local': '🧠 Project Learnings',
      };
      lines.push(`\n${labels[r.source] || r.source}:`);
      lastSource = r.source;
    }

    if (r.source === 'sessions') {
      lines.push(`  [${r.relevance}] ${r.startedAt.substring(0, 10)} | ${r.branch} (${r.sha}) — ${r.sessionId}`);
    } else if (r.source === 'tool-outputs') {
      lines.push(`  [${r.relevance}] ${r.file} — "${r.excerpt}"`);
    } else if (r.source === 'tool-log') {
      lines.push(`  [${r.relevance}] ${r.ts.substring(0, 19)} | ${r.tool} | ${r.chars.toLocaleString()} chars`);
    } else if (r.source.startsWith('learnings-')) {
      lines.push(`  [${r.relevance}] [${r.category}] ${r.content} (hits: ${r.hit_count}, last: ${r.last_seen.substring(0, 10)})`);
    }
  }

  lines.push('\n' + '═'.repeat(80));
  if (results.length === 0) {
    lines.push('No results found. Try broader terms or check that session data exists.');
  }
  lines.push('');

  return lines.join('\n');
}

// ─── Main ───────────────────────────────────────────────────────────────────

const args = parseArgs(process.argv.slice(2));

if (!args.query) {
  usage();
  process.exit(2);
}

// Collect results from requested sources
let allResults = [];

if (args.source === 'sessions' || args.source === 'all') {
  allResults = allResults.concat(searchSessions(args.query, args.limit));
}
if (args.source === 'tools' || args.source === 'all') {
  allResults = allResults.concat(searchToolOutputs(args.query, args.limit));
  allResults = allResults.concat(searchToolLog(args.query, args.limit));
}
if (args.source === 'learnings' || args.source === 'all') {
  allResults = allResults.concat(searchLearnings(args.query, args.limit));
}

// Sort by relevance across all sources
allResults.sort((a, b) => b.relevance - a.relevance);
allResults = allResults.slice(0, args.limit);

if (args.json) {
  process.stdout.write(JSON.stringify(allResults, null, 2) + '\n');
} else {
  process.stdout.write(formatText(allResults, args.query));
}

process.exit(allResults.length > 0 ? 0 : 1);
