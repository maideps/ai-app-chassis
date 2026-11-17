#!/usr/bin/env node
// Real-model eval baselines (feat-006): run both evals against the models you name and keep the
// reports as committed baselines next to each eval.
//
//   npm run setup:litellm                      once: installs the litellm extra into .venv
//   npm run eval:baseline -- --chat-model <litellm model> [--embedding-model <litellm model>]
//
// The chat model runs the template's summarize eval (APP_MODEL); the embedding model, when given,
// runs the retrieval eval (--embedder litellm:<model>). The provider key comes from the
// environment (ANTHROPIC_API_KEY, OPENAI_API_KEY, ...). A run in which any case errored is never
// saved: a score of 0 from a missing key must not look like a measurement. `fake/summarize` and
// `hashing` run the same path with the stand-ins, which is how the tests exercise it.

import { execFileSync, spawnSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SUMMARIZE_REPORT = "template/backend/evals/results/summarize.json";
const RETRIEVAL_REPORT = "core/evals/results/retrieval.json";
const BASELINE_DIRS = { summarize: "template/backend/evals/baselines", retrieval: "core/evals/retrieval/baselines" };

export const slug = (model) => model.replace(/[^A-Za-z0-9._-]+/g, "-");

// A report is a baseline only if every case ran: an errored case scores 0, which says nothing
// about the model. Returns the reason it cannot be saved, or null.
export function rejectReason(report) {
  if (!report || typeof report.score !== "number") return "the eval wrote no report";
  if (report.errors > 0) {
    const first = report.results.find((r) => r.error);
    return `${report.errors} of ${report.cases} cases errored, first: ${first?.id}: ${first?.error}`;
  }
  return null;
}

function python(args, env = process.env) {
  return spawnSync(process.execPath, [path.join(ROOT, "tools", "py.mjs"), ...args], {
    cwd: ROOT,
    encoding: "utf8",
    env,
  });
}

function fail(message) {
  console.error(`eval-baseline: ${message}`);
  process.exit(1);
}

function gitCommit() {
  try {
    return execFileSync("git", ["rev-parse", "--short", "HEAD"], { cwd: ROOT, encoding: "utf8" }).trim();
  } catch {
    return "unknown";
  }
}

function runEval(label, args, env, reportPath) {
  const run = python(args, env);
  process.stdout.write(run.stdout);
  if (run.status !== 0) fail(`${label} eval failed (exit ${run.status})\n${run.stderr.trim().split(/\r?\n/).slice(-15).join("\n")}`);
  const report = JSON.parse(readFileSync(path.join(ROOT, reportPath), "utf8"));
  const reason = rejectReason(report);
  if (reason) fail(`${label} run not saved: ${reason}`);
  return report;
}

function save(report, name, model, baselineDir) {
  const dir = path.resolve(ROOT, baselineDir ?? BASELINE_DIRS[name]);
  mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `${name}--${slug(model)}.json`);
  const baseline = { baseline: { eval: name, model, date: new Date().toISOString(), commit: gitCommit() }, ...report };
  writeFileSync(file, `${JSON.stringify(baseline, null, 2)}\n`, "utf8");
  return path.relative(ROOT, file).split(path.sep).join("/");
}

function parseArgs(argv) {
  const options = {};
  for (let i = 0; i < argv.length; i += 1) {
    const key = { "--chat-model": "chatModel", "--embedding-model": "embeddingModel", "--baseline-dir": "baselineDir" }[argv[i]];
    if (!key || !argv[i + 1]) fail(`usage: eval-baseline --chat-model <model> [--embedding-model <model>] [--baseline-dir <dir>] (got ${argv[i]})`);
    options[key] = argv[++i];
  }
  if (!options.chatModel) fail("--chat-model is required (a LiteLLM model name, or fake/summarize for a dry run)");
  return options;
}

function main() {
  const { chatModel, embeddingModel, baselineDir } = parseArgs(process.argv.slice(2));
  const needsLitellm = !chatModel.startsWith("fake/") || (embeddingModel && embeddingModel !== "hashing");
  if (needsLitellm && python(["-c", "import litellm"]).status !== 0) {
    fail("litellm is not installed in .venv: run npm run setup:litellm, then set your provider's API key");
  }

  const rows = [];
  // One model for the whole run: a per-step override would make the baseline lie about it.
  const env = { ...process.env, APP_MODEL: chatModel };
  delete env.APP_SUMMARIZE_MODEL;
  const summarize = runEval("summarize", ["-m", "app.evals"], env, SUMMARIZE_REPORT);
  const usage = summarize.metadata?.usage ?? {};
  if (!chatModel.startsWith("fake/") && !usage.cost_usd) {
    console.warn(`  [WARN] LiteLLM reported no cost for ${chatModel}; the baseline records $0`);
  }
  rows.push(["summarize keyword recall", chatModel, summarize.score, `${usage.input_tokens ?? 0} / ${usage.output_tokens ?? 0}`, `$${(usage.cost_usd ?? 0).toFixed(4)}`, save(summarize, "summarize", chatModel, baselineDir)]);

  if (embeddingModel) {
    const embedder = embeddingModel === "hashing" ? "hashing" : `litellm:${embeddingModel}`;
    const retrieval = runEval(
      "retrieval",
      ["-m", "ai_app_chassis.rag_eval", "--docs", "core/evals/retrieval/docs", "--golden", "core/evals/retrieval/golden.jsonl", "--out", RETRIEVAL_REPORT, "--k", "3", "--embedder", embedder],
      process.env,
      RETRIEVAL_REPORT,
    );
    rows.push([`retrieval recall@3 (MRR ${retrieval.metadata?.mrr})`, embeddingModel, retrieval.score, "—", "—", save(retrieval, "retrieval", embeddingModel, baselineDir)]);
  }

  console.log("\n| Eval | Model | Score | Tokens in / out | Cost | Baseline |\n|---|---|---|---|---|---|");
  for (const row of rows) console.log(`| ${row.join(" | ")} |`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main();
}
