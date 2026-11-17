import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { rejectReason, slug } from "../eval-baseline.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const SCRIPT = path.join(ROOT, "tools", "eval-baseline.mjs");

// No provider key ever reaches these runs, so a test can never spend money.
function envWithoutKeys() {
  const env = { ...process.env };
  for (const name of Object.keys(env)) if (/_API_KEY$/.test(name)) delete env[name];
  return env;
}

function run(args) {
  return spawnSync(process.execPath, [SCRIPT, ...args], { cwd: ROOT, encoding: "utf8", env: envWithoutKeys() });
}

test("slug keeps a model name usable as a file name", () => {
  assert.equal(slug("anthropic/claude-haiku-5-5"), "anthropic-claude-haiku-5-5");
  assert.equal(slug("litellm:openai/text-embedding-3-small"), "litellm-openai-text-embedding-3-small");
});

test("rejectReason refuses reports with errored cases or no score", () => {
  assert.equal(rejectReason({ score: 0.8, errors: 0, cases: 5, results: [] }), null);
  const errored = { score: 0, errors: 2, cases: 5, results: [{ id: "a" }, { id: "b", error: "AuthenticationError: no key" }] };
  assert.equal(rejectReason(errored), "2 of 5 cases errored, first: b: AuthenticationError: no key");
  assert.equal(rejectReason({}), "the eval wrote no report");
});

test("a dry run with the stand-ins writes both baselines with model, date and usage", () => {
  const dir = mkdtempSync(path.join(os.tmpdir(), "chassis-baseline-"));
  try {
    const result = run(["--chat-model", "fake/summarize", "--embedding-model", "hashing", "--baseline-dir", dir]);
    assert.equal(result.status, 0, `${result.stdout}${result.stderr}`);
    assert.deepEqual(readdirSync(dir).sort(), ["retrieval--hashing.json", "summarize--fake-summarize.json"]);
    const summarize = JSON.parse(readFileSync(path.join(dir, "summarize--fake-summarize.json"), "utf8"));
    assert.equal(summarize.baseline.model, "fake/summarize");
    assert.match(summarize.baseline.date, /^\d{4}-\d{2}-\d{2}T/);
    assert.equal(summarize.errors, 0);
    assert.equal(summarize.metadata.usage.calls, 5);
    const retrieval = JSON.parse(readFileSync(path.join(dir, "retrieval--hashing.json"), "utf8"));
    assert.equal(retrieval.metadata.k, 3);
    assert.match(result.stdout, /\| summarize keyword recall \| fake\/summarize \| 1 \|/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a real model without litellm, or without a key, saves nothing", () => {
  const dir = mkdtempSync(path.join(os.tmpdir(), "chassis-baseline-"));
  try {
    const result = run(["--chat-model", "openai/not-a-real-model", "--baseline-dir", dir]);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /litellm is not installed|cases errored|eval failed/);
    assert.deepEqual(readdirSync(dir), []);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("--chat-model is required", () => {
  const result = run([]);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /--chat-model is required/);
  assert.ok(!existsSync(path.join(ROOT, "template/backend/evals/baselines/summarize--undefined.json")));
});
