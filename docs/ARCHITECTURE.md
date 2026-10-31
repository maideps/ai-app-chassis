# Architecture

## Layer Model

Two Python packages, one depending on the other:

```
template/backend (package "app")          the example service; copied to start an app
  main.py        HTTP (FastAPI): /summarize, /usage, /health
  summarize.py   use case: guardrails -> prompt -> structured call; its fake handler
  wiring.py      the only place that picks a provider (fake or LiteLLM) from settings
  settings.py    environment configuration
  evals.py       golden-set eval of the use case
        |
        v  imports only the public API (ai_app_chassis.__init__)
core (package "ai_app_chassis")           no web framework, no database, only pydantic
  llm.py         provider port: LLMProvider, Message, Completion, Usage
  fake.py        deterministic provider for tests, evals and local runs
  litellm_provider.py  real models, imported lazily (optional extra)
  client.py      LLMClient: routing, structured output with retry, CallLedger
  prompts.py     versioned prompts on disk
  guardrails.py  input checks and PII redaction
  evals.py       golden-set runner and JSON report
```

## Harness Boundaries

The harness contract (described in `.harness/manifest.json` and enforced by `make check-arch` / `npm run check-arch`) separates:

- **CORE** — files that ship as-is and must not be edited (runner, scripts, templates, root operating manual).
- **TEMPLATES** — adopter skeletons under `templates/`.
- **INSTANCE** — this project's own state (feature list, progress, decisions, docs).
- **PRODUCT-OWNED** — directories listed in the manifest's `productRoots`.

Verification entrypoints delegate to the Node runner (`scripts/framework-check.mjs`); Makefile targets and npm scripts are 1:1 mirrors.

## Worktree Lanes

Multiple agents can work concurrently, each in its own sibling git worktree on branch `lane/<feature-id>` (`make lane-new F=<id>`, `lane-list`, `lane-land F=<id>`, `lane-drop F=<id>`). A branch can only be checked out in one worktree at a time, so git's own branch-checkout exclusivity is the coordination primitive — no lock file needed. WIP=1 is enforced per lane: a `lane/<feature-id>` branch may only activate the feature it is named for.

## Sharded Feature State

`feature_list.json` declares what each feature is and rarely changes; each feature's mutable state (`state`, `evidence`) lives in its own file, `.harness/state/<feature-id>.json`. `verify-feature` writes only that shard, never the shared declarations file — two lanes finishing two different features merge without conflict. `npm run migrate-feature-state` moves an older repo's inline state into shards.

## Application Dependency Rules

- `core` never imports `app`, FastAPI or any provider SDK at import time (LiteLLM is imported inside `LiteLLMProvider`).
- `app` uses the core through `LLMClient` and the port; only `wiring.py` names a concrete provider.
- Every model call goes through `LLMClient`, so it is routed per step and recorded in the ledger.
- Prompts live in `prompts/<name>/v<N>/`, never inline in code.
- Guardrails run before the model call, never after.

## Enforcement

```bash
make check-arch     # or: npm run check-arch
```

## Module Documentation

Co-locate architecture notes with the modules they affect; record framework-wide decisions in the root `DECISIONS.md`.
