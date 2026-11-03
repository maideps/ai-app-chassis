#!/usr/bin/env node
// create-app: start a new LLM-backed app from this chassis (feat-003).
//
//   node tools/create-app.mjs <target-dir> [--name <kebab-name>] [--core-path <dir>] [--plain] [--git]
//
// 1. Adopts the harness into <target-dir> with this repository's own copy of it, plus the
//    devcontainer and mcp components (--plain skips both).
// 2. Copies template/backend/ to backend/ and renames the `app` package after the project.
// 3. Writes the root files from template/scaffold/ ({{name}}, {{package}} filled in) and wires
//    the npm scripts, the quality gates, the CI workflow and the dev container for Python.
// The new app depends on the core through a pip direct reference: this repository on GitHub at
// the current commit, or a local core/ directory with --core-path (used by the tests).

import { execFileSync, spawnSync } from "node:child_process";
import {
  appendFileSync,
  cpSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  renameSync,
  statSync,
  writeFileSync,
} from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

export const CHASSIS_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const REPOSITORY = "https://github.com/maideps/ai-app-chassis.git";
const SKIPPED = new Set(["__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache", "results"]);
const PY_KEYWORDS = new Set(["and", "as", "class", "def", "del", "for", "from", "global", "import", "in", "is", "lambda", "not", "or", "pass", "return", "try", "while", "with", "yield"]);

export function packageName(name) {
  if (!/^[a-z][a-z0-9-]*[a-z0-9]$/.test(name) || name.includes("--")) {
    throw new Error(`invalid name "${name}": use lowercase letters, digits and single hyphens, e.g. ai-invoice-intake`);
  }
  const pkg = name.replace(/-/g, "_");
  if (PY_KEYWORDS.has(pkg) || pkg === "ai_app_chassis") {
    throw new Error(`"${name}" would give the Python package "${pkg}", which is reserved`);
  }
  return pkg;
}

// The pip requirement for the core: a local directory, or this repository at HEAD.
export function coreRequirement({ corePath } = {}) {
  if (corePath) return `ai-app-chassis @ ${pathToFileURL(path.resolve(corePath)).href}`;
  let ref = "main";
  try {
    ref = execFileSync("git", ["rev-parse", "HEAD"], { cwd: CHASSIS_ROOT, encoding: "utf8" }).trim();
    const pushed = execFileSync("git", ["branch", "-r", "--contains", ref], { cwd: CHASSIS_ROOT, encoding: "utf8" }).trim();
    if (!pushed) console.warn(`  [WARN] chassis commit ${ref.slice(0, 7)} is not on any remote branch yet; push it before installing the new app`);
  } catch {
    // Not a git checkout (an extracted copy): fall back to the default branch.
  }
  return `ai-app-chassis @ git+${REPOSITORY}@${ref}#subdirectory=core`;
}

function copyTree(src, dest) {
  mkdirSync(dest, { recursive: true });
  for (const entry of readdirSync(src, { withFileTypes: true })) {
    if (SKIPPED.has(entry.name) || entry.name.endsWith(".egg-info")) continue;
    const from = path.join(src, entry.name);
    const to = path.join(dest, entry.name);
    if (entry.isDirectory()) copyTree(from, to);
    else cpSync(from, to);
  }
}

function filesUnder(dir, extensions) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) return filesUnder(full, extensions);
    return extensions.some((ext) => entry.name.endsWith(ext)) ? [full] : [];
  });
}

function edit(file, transform) {
  const before = readFileSync(file, "utf8");
  const after = transform(before);
  if (after !== before) writeFileSync(file, after, "utf8");
}

function replaceOnce(text, search, replacement, where) {
  if (!text.includes(search)) throw new Error(`create-app: expected text not found in ${where}: ${search.split("\n")[0]}`);
  return text.replace(search, replacement);
}

// Rename the template's `app` package and its chassis-app identity after the new project.
function renameBackend(backend, { name, pkg, core }) {
  renameSync(path.join(backend, "src", "app"), path.join(backend, "src", pkg));
  for (const file of filesUnder(backend, [".py"])) {
    edit(file, (text) =>
      text
        .replace(/\bfrom app(\.| import\b)/g, `from ${pkg}$1`)
        .replace(/^import app\b/gm, `import ${pkg}`)
        .replace(/uvicorn app\.main:app --reload`` from template\/backend/g, `uvicorn ${pkg}.main:app --reload\`\` from backend`)
        .replace(/chassis-app-eval/g, `${name}-eval`)
        .replace(/FastAPI\(title="chassis-app"\)/g, `FastAPI(title="${name}")`)
        .replace(/^"""Example app built on ai-app-chassis\. Copy this folder to start a new LLM-backed service\."""/m, `"""${name}: an LLM-backed service built on ai-app-chassis."""`),
    );
  }
  edit(path.join(backend, "pyproject.toml"), (text) =>
    text
      .replace(/^name = "chassis-app"$/m, `name = "${name}"`)
      .replace(/^description = ".*"$/m, `description = "${name}: an LLM-backed service built on ai-app-chassis."`)
      .replace(/"ai-app-chassis",/, `${JSON.stringify(core)},`)
      .replace(/^chassis-app-eval = "app\.evals:main"$/m, `${name}-eval = "${pkg}.evals:main"`)
      .replace(/^app = \["prompts/m, `${pkg} = ["prompts`),
  );
}

function renderScaffold(target, vars) {
  const scaffold = path.join(CHASSIS_ROOT, "template", "scaffold");
  for (const file of filesUnder(scaffold, [""])) {
    const rel = path.relative(scaffold, file);
    const dest = path.join(target, rel);
    mkdirSync(path.dirname(dest), { recursive: true });
    const text = readFileSync(file, "utf8").replace(/\{\{(name|package)\}\}/g, (_, key) => vars[key]);
    writeFileSync(dest, text, "utf8");
  }
}

function wireScripts(target, pythonPackage) {
  const file = path.join(target, "package.json");
  const pkg = JSON.parse(readFileSync(file, "utf8"));
  const py = "node tools/py.mjs";
  const scripts = {
    ...pkg.scripts,
    lint: `node scripts/framework-check.mjs lint && ${py} -m ruff check backend && ${py} -m ruff format --check backend`,
    typecheck: `node scripts/framework-check.mjs typecheck && ${py} -m mypy --config-file backend/pyproject.toml backend/src`,
    test: `node scripts/framework-check.mjs test && ${py} -m pytest -q -p no:cacheprovider backend/tests`,
    build: `node scripts/framework-check.mjs build && ${py} -m compileall -q backend/src`,
    e2e: "node scripts/framework-check.mjs e2e",
  };
  // The chassis's own extra scripts (setup:python, eval) are rewritten for backend/.
  const ordered = {};
  for (const [key, value] of Object.entries(scripts)) {
    if (key === "setup:python" || key === "eval") continue;
    ordered[key] = value;
    if (key === "setup") ordered["setup:python"] = `${py} setup`;
    if (key === "quality") ordered.eval = `${py} -m ${pythonPackage}.evals`;
  }
  pkg.scripts = ordered;
  writeFileSync(file, `${JSON.stringify(pkg, null, 2)}\n`, "utf8");
}

function wireManifest(target) {
  const file = path.join(target, ".harness", "manifest.json");
  edit(file, (text) => text.replace(/"productRoots": \[[^\]]*\]/, '"productRoots": [\n    "backend/",\n    "tools/"\n  ]'));
}

// .harness/arch-rules.json travels with the harness, so it also carries this chassis's own
// rules (arch-1NN, D-004), which check files the new app does not have. Keep the harness's.
function wireArchRules(target) {
  const file = path.join(target, ".harness", "arch-rules.json");
  const rules = JSON.parse(readFileSync(file, "utf8"));
  rules.rules = rules.rules.filter((rule) => /^arch-0\d\d$/.test(rule.id));
  writeFileSync(file, `${JSON.stringify(rules, null, 2)}\n`, "utf8");
}

function wireCi(target) {
  const file = path.join(target, ".github", "workflows", "ci.yml");
  edit(file, (text) => {
    if (text.includes("setup:python")) return text;
    const setupPython = text.includes("actions/setup-python")
      ? ""
      : '      - uses: actions/setup-python@v5\n        with:\n          python-version: "3.12"\n\n';
    return replaceOnce(
      text,
      "      - name: Install and set up project\n        run: npm run setup --if-present\n",
      `${setupPython}      - name: Install and set up project\n        run: npm run setup --if-present\n\n      - name: Install the Python backend with its dev tools\n        run: npm run setup:python\n`,
      file,
    );
  });
}

function wireDevcontainer(target, name) {
  const file = path.join(target, ".devcontainer", "devcontainer.json");
  if (!existsSync(file)) return;
  const config = JSON.parse(readFileSync(file, "utf8"));
  config.name = name;
  config.features["ghcr.io/devcontainers/features/python:1"] ??= { version: "3.12" };
  writeFileSync(file, `${JSON.stringify(config, null, 2)}\n`, "utf8");
  edit(path.join(target, ".devcontainer", "post-create.sh"), (text) =>
    text.includes("tools/py.mjs setup")
      ? text
      : replaceOnce(text, "\n./init.sh ", "\n# The Python layers run from .venv (backend/, editable).\nnode tools/py.mjs setup\n\n./init.sh ", "post-create.sh"),
  );
}

const GITIGNORE = `
# Python
.venv/
__pycache__/
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage

# Eval reports are regenerated by the quality gate
backend/evals/results/
`;

function runIn(target, script, args = []) {
  const result = spawnSync(process.execPath, [path.join(target, script), ...args], { cwd: target, encoding: "utf8" });
  if (result.status !== 0) throw new Error(`create-app: ${script} ${args.join(" ")} failed\n${result.stdout}${result.stderr}`);
}

export function createApp(targetDir, { name, corePath, plain = false, git = false } = {}) {
  const target = path.resolve(targetDir);
  const appName = name ?? path.basename(target);
  const pkg = packageName(appName);
  if (existsSync(target) && (!statSync(target).isDirectory() || readdirSync(target).length > 0)) {
    throw new Error(`create-app: ${target} exists and is not an empty directory`);
  }
  const core = coreRequirement({ corePath });

  const components = plain ? [] : ["--with", "devcontainer", "--with", "mcp"];
  const adopt = spawnSync(process.execPath, [path.join(CHASSIS_ROOT, "scripts", "create-harness.mjs"), target, ...components], { encoding: "utf8" });
  if (adopt.status !== 0) throw new Error(`create-app: create-harness failed\n${adopt.stdout}${adopt.stderr}`);

  copyTree(path.join(CHASSIS_ROOT, "template", "backend"), path.join(target, "backend"));
  renameBackend(path.join(target, "backend"), { name: appName, pkg, core });
  renderScaffold(target, { name: appName, package: pkg });
  wireScripts(target, pkg);
  wireManifest(target);
  wireArchRules(target);
  wireCi(target);
  wireDevcontainer(target, appName);
  appendFileSync(path.join(target, ".gitignore"), GITIGNORE, "utf8");

  // Derived files follow the new scripts and feature list.
  runIn(target, "scripts/harness-docs.mjs");
  runIn(target, "scripts/framework-check.mjs", ["progress-update"]);
  if (git) execFileSync("git", ["init", "-q", "-b", "main"], { cwd: target });
  return { target, name: appName, package: pkg, core };
}

function main() {
  const args = process.argv.slice(2);
  const options = {};
  const positional = [];
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === "--name") options.name = args[++i];
    else if (arg === "--core-path") options.corePath = args[++i];
    else if (arg === "--plain") options.plain = true;
    else if (arg === "--git") options.git = true;
    else if (arg.startsWith("--")) {
      console.error(`unknown option ${arg}`);
      process.exit(1);
    } else positional.push(arg);
  }
  if (positional.length !== 1) {
    console.error("usage: node tools/create-app.mjs <target-dir> [--name <kebab-name>] [--core-path <dir>] [--plain] [--git]");
    process.exit(1);
  }
  try {
    const result = createApp(positional[0], options);
    console.log(`=== create-app: ${result.target} ===`);
    console.log(`  Project ${result.name}, Python package ${result.package}`);
    console.log(`  Core dependency: ${result.core}`);
    console.log("");
    console.log("  Next steps:");
    console.log(`  1. cd ${result.target}`);
    console.log("  2. npm run setup:python");
    console.log("  3. CW_SKIP_ADOPTION_MATRIX=1 npm run check");
    console.log("  4. Replace the example use case (see README.md, Next steps).");
  } catch (err) {
    console.error(err.message);
    process.exit(1);
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main();
}
