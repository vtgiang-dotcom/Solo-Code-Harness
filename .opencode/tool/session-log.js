/**
 * session-log.js — Custom OpenCode tool for session logging.
 *
 * Records session metadata to .opencode/state/usage.jsonl
 * for cost estimation and session history tracking.
 *
 * Usage: OpenCode auto-discovers tools from .opencode/tool/*.js
 */
import { tool } from "@opencode-ai/plugin";
import { z } from "zod";
import { appendFileSync, existsSync, mkdirSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..", "..");
const STATE_DIR = resolve(ROOT, ".opencode", "state");
const LOG_FILE = resolve(STATE_DIR, "usage.jsonl");

export const sessionLog = tool({
  description:
    "Record session metadata for cost tracking and history. Call this at the end of every session.",

  args: {
    model: z
      .string()
      .optional()
      .describe("Model used (e.g., deepseek-v4-pro)"),
    duration_min: z
      .number()
      .optional()
      .describe("Session duration in minutes"),
    token_count: z
      .number()
      .optional()
      .describe("Approximate tokens consumed"),
    summary: z
      .string()
      .optional()
      .describe("One-line summary of what was accomplished"),
  },

  async execute(args, ctx) {
    try {
      if (!existsSync(STATE_DIR)) mkdirSync(STATE_DIR, { recursive: true });

      const entry = {
        timestamp: new Date().toISOString(),
        model: args.model || "unknown",
        duration_min: args.duration_min || 0,
        token_count: args.token_count || 0,
        summary: args.summary || "",
      };

      appendFileSync(LOG_FILE, JSON.stringify(entry) + "\n", "utf-8");

      return {
        output: `Session logged: ${entry.timestamp}\nModel: ${entry.model}\nDuration: ${entry.duration_min}min`,
        title: "Session Logged",
        metadata: entry,
      };
    } catch (err) {
      return {
        output: `Failed to log session: ${err.message}`,
        title: "Session Log Error",
      };
    }
  },
});
