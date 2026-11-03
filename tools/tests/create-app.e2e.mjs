#!/usr/bin/env node
// End-to-end check of create-app (feat-003): generate an app against this checkout's core/,
// install it, and run its own verification. Slow (a fresh venv and a pip install), so it runs
// in the e2e layer, not in npm run test.

import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";

import { CHASSIS_ROOT, createApp } from "../create-app.mjs";

const parent = mkdtempSync(path.join(os.tmpdir(), "chassis-e2e-"));
const target = path.join(parent, "ai-e2e-app");
let failed = false;

function step(label, cmd, args) {
  const result = spawnSync(cmd, args, {
    cwd: target,
    encoding: "utf8",
    shell: process.platform === "win32",
    env: { ...process.env, CW_SKIP_ADOPTION_MATRIX: "1" },
  });
  if (result.status === 0) {
    console.log(`  [PASS] ${label}`);
    return `${result.stdout}${result.stderr}`;
  }
  failed = true;
  console.log(`  [FAIL] ${label} (exit ${result.status})`);
  console.log(`${result.stdout}${result.stderr}`.split(/\r?\n/).slice(-40).join("\n"));
  return "";
}

console.log("=== create-app end to end ===");
try {
  createApp(target, { corePath: path.join(CHASSIS_ROOT, "core"), git: true });
  console.log(`  [PASS] generated ${target}`);
  step("npm run setup:python", "npm", ["run", "setup:python"]);
  if (!failed) {
    step("git add -A", "git", ["add", "-A"]);
    const check = step("npm run check in the generated app", "npm", ["run", "check"]);
    for (const line of check.split(/\r?\n/).filter((l) => /\[(PASS|FAIL)\] (coverage|eval)/.test(l))) {
      console.log(`    ${line.trim()}`);
    }
    step("npm run check-arch in the generated app", "npm", ["run", "check-arch"]);
  }
} catch (err) {
  failed = true;
  console.log(`  [FAIL] ${err.message}`);
} finally {
  rmSync(parent, { recursive: true, force: true });
}
process.exit(failed ? 1 : 0);
