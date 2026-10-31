# Product Overview

ai-app-chassis is the runtime starting point for LLM-backed apps: a Python core library with the pieces every such app repeats (provider port, deterministic fake, model routing, cost ledger, structured output, versioned prompts, guardrails, evals) and an app template built on it.

## Primary Users

- Me, starting the next portfolio app (`ai-<thing>-<function>`) without rewriting the AI layer again.
- AI coding agents working on those apps: the fake model and the eval gate let them verify AI behavior without a key.

## Key User Flows

- Install and verify: `npm run setup:python`, then `npm run check` (layers plus the coverage and eval gates).
- Build a use case: add a Pydantic output model, a prompt folder and a fake handler, then call `LLMClient.structured` from the app.
- Change a prompt safely: add `prompts/<name>/v<N+1>/`, run `npm run eval`, compare the score with the previous version.
- Switch to a real model: set `APP_MODEL` (and optionally per-step models) to a LiteLLM model name.

## Out of Scope (for now)

- Publishing the core to PyPI.
- A frontend, a RAG module and a `create-app` generator (planned features).
