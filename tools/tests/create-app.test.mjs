import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";

import { CHASSIS_ROOT, coreRequirement, createApp, packageName } from "../create-app.mjs";
import { validateQualityConfig } from "../../scripts/quality-gates.mjs";

function tempTarget(name = "ai-demo-notes") {
  return path.join(mkdtempSync(path.join(os.tmpdir(), "chassis-create-app-")), name);
}

function filesUnder(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    return entry.isDirectory() ? filesUnder(full) : [full];
  });
}

const read = (root, rel) => readFileSync(path.join(root, rel), "utf8");

test("packageName turns a kebab-case project name into a Python package", () => {
  assert.equal(packageName("ai-invoice-intake"), "ai_invoice_intake");
  for (const bad of ["AI-Thing", "-x", "x-", "a--b", "class", "ai-app-chassis"]) {
    assert.throws(() => packageName(bad), /invalid name|reserved/, bad);
  }
});

test("coreRequirement pins a local core path or this repository on GitHub", () => {
  assert.match(coreRequirement({ corePath: path.join(CHASSIS_ROOT, "core") }), /^ai-app-chassis @ file:\/\/\/.*core$/);
  assert.match(
    coreRequirement(),
    /^ai-app-chassis @ git\+https:\/\/github\.com\/maideps\/ai-app-chassis\.git@([0-9a-f]{40}|main)#subdirectory=core$/,
  );
});

test("createApp renames the template package and wires the project around it", () => {
  const target = tempTarget();
  try {
    const result = createApp(target, { corePath: path.join(CHASSIS_ROOT, "core") });
    assert.equal(result.package, "ai_demo_notes");

    // The package is renamed everywhere it is imported, and no cache came along.
    assert.ok(existsSync(path.join(target, "backend/src/ai_demo_notes/main.py")));
    assert.ok(!existsSync(path.join(target, "backend/src/app")));
    for (const file of filesUnder(path.join(target, "backend"))) {
      assert.doesNotMatch(file, /__pycache__|\.mypy_cache|\.ruff_cache|egg-info|evals[\\/]results/);
      if (/\.(py|toml)$/.test(file)) {
        const text = readFileSync(file, "utf8");
        assert.doesNotMatch(text, /\bfrom app\b|^import app\b|chassis-app/m, file);
      }
    }
    const pyproject = read(target, "backend/pyproject.toml");
    assert.match(pyproject, /^name = "ai-demo-notes"$/m);
    assert.match(pyproject, /"ai-app-chassis @ file:\/\/\/[^"]+core"/);
    assert.match(pyproject, /^ai-demo-notes-eval = "ai_demo_notes\.evals:main"$/m);
    assert.match(pyproject, /^ai_demo_notes = \["prompts/m);
    assert.match(read(target, "backend/src/ai_demo_notes/main.py"), /FastAPI\(title="ai-demo-notes"\)/);

    // Root files come from the scaffold with every placeholder filled.
    for (const rel of ["README.md", "docs/PRODUCT.md", "docs/quality-document.md", "feature_list.json", "tools/py.mjs", ".harness/quality.json"]) {
      assert.doesNotMatch(read(target, rel), /\{\{\w+\}\}/, rel);
    }
    assert.match(read(target, "tools/py.mjs"), /import ai_demo_notes, ai_app_chassis/);
    const quality = JSON.parse(read(target, ".harness/quality.json"));
    assert.deepEqual(validateQualityConfig(quality), []);
    assert.equal(quality.enabled, true);

    // Scripts, manifest, rules, CI and dev container are wired for backend/.
    const scripts = JSON.parse(read(target, "package.json")).scripts;
    assert.equal(scripts["setup:python"], "node tools/py.mjs setup");
    assert.equal(scripts.eval, "node tools/py.mjs -m ai_demo_notes.evals");
    assert.match(scripts.test, /pytest -q -p no:cacheprovider backend\/tests$/);
    assert.doesNotMatch(Object.values(scripts).join("\n"), /core\/|template\//);
    assert.deepEqual(JSON.parse(read(target, ".harness/manifest.json")).productRoots, ["backend/", "tools/"]);
    const ruleIds = JSON.parse(read(target, ".harness/arch-rules.json")).rules.map((rule) => rule.id);
    assert.ok(ruleIds.length > 0 && ruleIds.every((id) => /^arch-0\d\d$/.test(id)), ruleIds.join(","));
    const ci = read(target, ".github/workflows/ci.yml");
    assert.equal(ci.match(/actions\/setup-python/g)?.length, 1);
    assert.match(ci, /run: npm run setup:python/);
    const devcontainer = JSON.parse(read(target, ".devcontainer/devcontainer.json"));
    assert.equal(devcontainer.name, "ai-demo-notes");
    assert.ok("ghcr.io/devcontainers/features/python:1" in devcontainer.features);
    assert.match(read(target, ".devcontainer/post-create.sh"), /node tools\/py\.mjs setup\n\n\.\/init\.sh/);
    assert.ok(existsSync(path.join(target, ".mcp.json")));
    assert.match(read(target, ".gitignore"), /^backend\/evals\/results\/$/m);
  } finally {
    rmSync(path.dirname(target), { recursive: true, force: true });
  }
});

test("a generated app passes the harness lint and classifies every file it tracks", () => {
  const target = tempTarget("ai-lint-check");
  try {
    createApp(target, { name: "ai-lint-check", corePath: path.join(CHASSIS_ROOT, "core"), git: true });
    execFileSync("git", ["add", "-A"], { cwd: target });
    for (const mode of ["lint", "typecheck", "build", "manifest"]) {
      const result = spawnSync(process.execPath, ["scripts/framework-check.mjs", mode], { cwd: target, encoding: "utf8" });
      assert.equal(result.status, 0, `${mode}\n${result.stdout}${result.stderr}`);
    }
  } finally {
    rmSync(path.dirname(target), { recursive: true, force: true });
  }
});

test("--plain skips the optional components, and a non-empty target is refused", () => {
  const target = tempTarget("ai-plain");
  try {
    createApp(target, { corePath: path.join(CHASSIS_ROOT, "core"), plain: true });
    assert.ok(!existsSync(path.join(target, ".devcontainer")));
    assert.ok(!existsSync(path.join(target, ".mcp.json")));

    const occupied = path.join(path.dirname(target), "occupied");
    mkdirSync(occupied);
    writeFileSync(path.join(occupied, "keep.txt"), "x");
    assert.throws(() => createApp(occupied, { name: "ai-occupied" }), /exists and is not an empty directory/);
    assert.equal(read(occupied, "keep.txt"), "x");
  } finally {
    rmSync(path.dirname(target), { recursive: true, force: true });
  }
});
