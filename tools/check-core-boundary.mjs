#!/usr/bin/env node
// arch-101: the core library stays framework-free. No module under core/src may import the
// template app, a web framework, or a provider SDK at module level; LiteLLM is the one SDK,
// and it is imported inside LiteLLMProvider.__init__ only. Prints PASS or the offending lines.

import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const core = path.join(root, "core", "src", "ai_app_chassis");
const FORBIDDEN = /^(?:from|import)\s+(app|fastapi|starlette|litellm|openai|anthropic)\b/;

const violations = [];
for (const name of readdirSync(core).filter((file) => file.endsWith(".py"))) {
  readFileSync(path.join(core, name), "utf8")
    .split(/\r?\n/)
    .forEach((line, index) => {
      // Top-level imports only: an indented import runs lazily inside a function.
      if (FORBIDDEN.test(line)) violations.push(`core/src/ai_app_chassis/${name}:${index + 1}: ${line.trim()}`);
    });
}

if (violations.length > 0) {
  for (const violation of violations) console.log(violation);
  process.exit(1);
}
console.log("PASS");
