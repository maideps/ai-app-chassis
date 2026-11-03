# Architectural Decisions Log

This file records significant architectural decisions, their context, alternatives considered, and consequences. It serves as durable cross-session memory for why the codebase is structured the way it is.

## Decision Template

```
### D-XXX: [Decision Title]

**Date:** YYYY-MM-DD
**Status:** proposed | accepted | deprecated | superseded by D-YYY
**Context:** [What problem are we solving? What constraints exist?]
**Decision:** [What did we decide to do?]
**Alternatives considered:**
- Alternative 1: [description] — Rejected because [reason]
**Consequences:**
- Positive: [benefits gained]
- Negative: [tradeoffs accepted]
```

## Recorded Decisions

<!-- Add decision records here, newest last. Expand long records into docs/decisions/ and link back from here. -->

## Decisions

### D-001: One repository, two pieces: a core library and an app template

**Date:** 2026-10-30
**Status:** accepted
**Context:** ai-issue-triage and ai-invoice-intake each wrote their own provider port, fake model, structured-output handling and cost tracking. Copying that layer into every new app makes fixes land in one app only.
**Decision:** `core/` is an installable library (`ai_app_chassis`) for what every app shares; `template/backend/` is an app that uses only its public API and is copied to start a new app. Both live in one repository so a core change and its template adjustment land in the same commit, and CI tests the template against the current core.
**Alternatives considered:**
- Two repositories (core, starter) — rejected for now: one maintainer, and both evolve together; split only if someone uses the core without the template.
- Everything in the template — rejected: copied code drifts, which is the problem being solved.
- Inside ai-harness-framework — rejected: the harness is stack-agnostic Node tooling; this is Python runtime code.
**Consequences:**
- Positive: one place to fix the AI layer; the template is always a working example of the core.
- Negative: apps created from the template must install the core from this repository until it is published.

### D-002: The core depends on pydantic only; providers and web frameworks stay outside

**Date:** 2026-10-30
**Status:** accepted
**Context:** A core that imports FastAPI or a provider SDK forces every app to install them and couples tests to the network.
**Decision:** The core's only runtime dependency is pydantic. LiteLLM is an optional extra imported inside `LiteLLMProvider`. The default model everywhere is the deterministic fake (`fake/<handler>`), so tests and evals need no key. arch-101 (`tools/check-core-boundary.mjs`) fails on a top-level import of the app, FastAPI/Starlette or a provider SDK in the core.
**Alternatives considered:**
- Depend on LiteLLM directly — rejected: a heavy install and network access for code that tests never need.
**Consequences:**
- Positive: the core installs in seconds and its tests are deterministic.
- Negative: `LiteLLMProvider` is untested until a real-model run (feat-006).

### D-003: Coverage and the template's eval score are quality gates from day one

**Date:** 2026-10-30
**Status:** accepted
**Context:** The harness quality gates (its D-033) exist for exactly this kind of project: a prompt or code change can keep tests green and still make the output worse.
**Decision:** `.harness/quality.json` enables two gates: line coverage of `ai_app_chassis` and `app` (floor 90, measured 93.61) and the summarize golden-set keyword recall (floor 0.8, measured 1.0).
**Alternatives considered:**
- Start with gates disabled — rejected: the floors are cheap to meet now and expensive to retrofit.
**Consequences:**
- Positive: `npm run check` fails when coverage or the eval score drops.
- Negative: the eval floor only means something with a real model; on the fake it proves the pipeline, not quality (stated in the README).

### D-004: create-app generates an app around a renamed copy of the template, with the core pinned by commit

**Date:** 2026-11-03
**Status:** accepted
**Context:** D-001 said a new app starts by copying `template/backend/`. By hand that means renaming the package, writing a launcher, wiring npm scripts, quality gates, CI and the dev container for Python, and adopting the harness. Each step is easy to get wrong, and the result is only known to work once the new app passes its own `npm run check`.
**Decision:**
- `tools/create-app.mjs` (`npm run create-app -- <dir>`) runs this repository's copy of `create-harness` (devcontainer and mcp unless `--plain`), copies `template/backend/` to `backend/` without caches, renames the `app` package and the `chassis-app` identity, and renders `template/scaffold/` (`{{name}}`, `{{package}}`) for the root files the harness would otherwise leave as placeholders.
- The core dependency is a pip direct reference to this repository at the current commit (`git+...@<sha>#subdirectory=core`), so an app keeps building the same core until it bumps the pin; `--core-path` uses a local `core/` (the tests use it).
- Project-specific architecture rules in this repository use ids `arch-1NN`; the harness's use `arch-0NN`. `create-app` keeps only the harness's, because the chassis rules check files a new app does not have.
- A slow end-to-end check (`tools/tests/create-app.e2e.mjs`, in `npm run e2e`) installs a generated app and runs its own `npm run check` and `check-arch`.
**Alternatives considered:**
- A cookiecutter/copier template — rejected: another tool to install, and the harness adoption step is Node anyway.
- Depend on `ai-app-chassis` from PyPI — rejected until the core is published.
- Pin the core to `main` — rejected: every app would silently pick up core changes.
**Consequences:**
- Positive: a new app is one command away and is verified the same way as this repository.
- Negative: generating from an unpushed commit gives an app whose pin cannot be installed yet (create-app warns); the e2e check needs network for PyPI and adds about two minutes to `npm run check`.
