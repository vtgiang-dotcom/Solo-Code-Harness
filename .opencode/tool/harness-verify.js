/**
 * harness-verify.js — Custom OpenCode tool for Solo-Code verification gates.
 *
 * Provides structured pass/fail results from all 6 verification gates
 * instead of requiring the agent to parse unstructured bash output.
 *
 * Usage: OpenCode auto-discovers tools from .opencode/tool/*.js
 */
import { tool } from "@opencode-ai/plugin";
import { z } from "zod";
import { execSync } from "child_process";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..", "..");

const GATES = {
  lint: {
    label: "Lint (ruff)",
    command: `ruff check .`,
    cwd: ROOT,
  },
  schema: {
    label: "Schema Validation",
    command: `python tools/validate_schemas.py`,
    cwd: ROOT,
  },
  garden: {
    label: "Garden (drift detection)",
    command: `python tools/garden.py`,
    cwd: ROOT,
  },
  test: {
    label: "Harness Tests",
    command: `python -m pytest tools/test_harness.py -q`,
    cwd: ROOT,
  },
  security: {
    label: "Security Scan",
    command: `python .github/scripts/security_scan.py .`,
    cwd: ROOT,
  },
  guard: {
    label: "Guard Plugin Tests",
    command: `node .opencode/tests/test-guard.mjs`,
    cwd: ROOT,
  },
};

function runGate(name) {
  const gate = GATES[name];
  if (!gate) return { gate: name, passed: false, error: `Unknown gate: ${name}` };

  try {
    const stdout = execSync(gate.command, {
      cwd: gate.cwd,
      encoding: "utf-8",
      timeout: 30_000,
      stdio: ["ignore", "pipe", "pipe"],
    });
    const stderr = ""; // stderr merged if we used pipe, but execSync throws on non-zero
    return {
      gate: name,
      label: gate.label,
      passed: true,
      output: stdout.trim().split("\n").slice(-3).join("\n"), // last 3 lines summary
    };
  } catch (err) {
    return {
      gate: name,
      label: gate.label,
      passed: false,
      error: err.stderr?.trim().split("\n").slice(0, 5).join("\n") || err.message,
    };
  }
}

export const harnessVerify = tool({
  description:
    "Run Solo-Code verification gates and return structured pass/fail results. Gates: lint, schema, garden, test, security, guard. Default: all.",

  args: {
    gates: z
      .array(z.enum(["lint", "schema", "garden", "test", "security", "guard"]))
      .optional()
      .describe("Which gates to run (default: all 6)"),
  },

  async execute(args, ctx) {
    const selected = args.gates?.length ? args.gates : Object.keys(GATES);
    const results = selected.map((g) => runGate(g));

    const passed = results.filter((r) => r.passed).length;
    const failed = results.filter((r) => !r.passed);
    const allPassed = failed.length === 0;

    const output = [
      `## Verification Results: ${allPassed ? "ALL PASSED" : `${failed.length} FAILED`}`,
      "",
      ...results.map((r) => {
        const icon = r.passed ? "✅" : "❌";
        const detail = r.passed ? r.output : r.error;
        return `${icon} **${r.label}**: ${r.passed ? "PASS" : "FAIL"}\n   ${detail || ""}`;
      }),
      "",
      `**Summary**: ${passed}/${results.length} passed.`,
      allPassed ? "No issues found." : `Failed gates: ${failed.map((f) => f.gate).join(", ")}`,
    ].join("\n");

    return {
      output,
      title: `Verification: ${passed}/${results.length} passed`,
      metadata: {
        passed,
        total: results.length,
        failed: failed.map((f) => f.gate),
        allPassed,
      },
    };
  },
});
