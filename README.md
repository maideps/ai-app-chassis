# ai-app-chassis

[![ci](https://github.com/maideps/ai-app-chassis/actions/workflows/ci.yml/badge.svg)](https://github.com/maideps/ai-app-chassis/actions/workflows/ci.yml)

The chassis I build LLM-backed apps on: a small Python core library for the parts every AI app repeats, and an app template that already uses it, with tests, guardrails and an eval gate from the first commit.

> **Portfolio project.** This is a skeleton extracted from my own apps (ai-issue-triage and ai-invoice-intake), not a published framework. It runs end to end on a deterministic fake model; real-model runs need a LiteLLM model name and its key.

See the [Harness Command Reference](docs/HARNESS.md) for every make target and npm script.

## What is in it

| Piece | Where | What it gives an app |
|---|---|---|
| Provider port | `core/src/ai_app_chassis/llm.py` | `LLMProvider`, `Message`, `Completion`, `Usage`: the only shape the app sees of a model |
| Fake provider | `fake.py` | No key, no network, same answer every time; handlers per step, and a schema-valid default for anything else |
| Real models | `litellm_provider.py` | Any LiteLLM model (`pip install 'ai-app-chassis[litellm]'`) |
| Client | `client.py` | Per-step model routing, structured output validated with Pydantic (one retry with the error shown to the model), a ledger of tokens, cost and p50/p95 latency |
| Prompts | `prompts.py` | Versioned prompts on disk (`prompts/<name>/v<N>/`), `latest` or a pinned version, ids like `summarize/v1` in the ledger |
| Guardrails | `guardrails.py` | Input length, prompt-injection phrases, e-mail and phone redaction, all before the model is called |
| Evals | `evals.py` | Golden-set runner with custom scorers and a JSON report whose `score` a quality gate reads |
| App template | `template/backend/` | FastAPI service with `/summarize`, `/usage` and `/health`, its prompt, its fake handler, a five-case golden set and tests |

## Run it in five minutes

Needs Node 18+ and Python 3.11+.

```bash
npm run setup:python      # creates .venv and installs core/ and template/backend/ in editable mode
npm run check             # lint, types, tests, build, then the quality gates
npm run eval              # golden-set eval of the template, report in template/backend/evals/results/
```

Run the API on the fake model:

```bash
cd template/backend
../../.venv/Scripts/python -m uvicorn app.main:app --reload    # .venv/bin/python on macOS and Linux
curl -X POST localhost:8000/summarize -H "content-type: application/json" -d '{"text": "Offline sync ships today. Sync keeps drafts on the device."}'
```

Use a real model by setting `APP_MODEL` (for example `openai/gpt-4o-mini`) and its provider key, after `pip install -e './core[litellm]'`. `APP_SUMMARIZE_MODEL` overrides the model for the summarize step only.

## Quality gates

`.harness/quality.json` turns two numbers into floors, checked by `npm run quality` and at the end of `npm run check`:

| Gate | Floor | Current (fake model) |
|---|---|---|
| Line coverage of `ai_app_chassis` and `app` | 90 | 93.61 |
| Golden-set keyword recall of `/summarize` | 0.8 | 1.0 |

The eval score is 1.0 because the fake summarizer is deterministic and the golden set was written against it: it proves the eval pipeline, not model quality. Rerun `npm run eval` with a real `APP_MODEL` for a meaningful number.

## Starting a new app from the template

```bash
npm run create-app -- ../ai-new-app                   # or: node tools/create-app.mjs <dir> --name <kebab-name>
cd ../ai-new-app && npm run setup:python && npm run check
```

`create-app` adopts the harness into the new directory (with the dev container and the context7 MCP server; `--plain` skips both), copies `template/backend/` to `backend/` with the `app` package renamed after the project (`ai_new_app`), and writes the root files from `template/scaffold/`: README, product and quality docs, a feature list, the Python launcher and the quality gates. The npm scripts, the CI workflow and the dev container are wired for Python. The new app installs the core from this repository on GitHub, pinned to the current commit, so push before generating; `--core-path <dir>` points at a local `core/` instead.

Then replace the example: a Pydantic output model, a prompt folder and a fake handler for the real use case, and golden cases for its eval gate.

A frontend in the template and an optional RAG module are planned (see `feature_list.json`).

## Stack

Python 3.11+, Pydantic 2, FastAPI, LiteLLM (optional), pytest, ruff, mypy (strict). Built and verified with [ai-harness-framework](https://github.com/maideps/ai-harness-framework): feature list, verification layers, quality gates, a dev container with Claude Code, Codex and Gemini CLI, and the context7 MCP server.

## Repository layout

The product is in `core/` (the `ai_app_chassis` library and its tests) and `template/` (the FastAPI app template). Note the singular: `template/` is the app template, while `templates/` belongs to the harness. The rest of the root is the process record from [ai-harness-framework](https://github.com/maideps/ai-harness-framework), the workflow this project is built with. `AGENTS.md` is the workflow every agent follows, and `CLAUDE.md`, `GEMINI.md` and `codex.md` point each agent to it. `scripts/`, `tools/`, `templates/`, `skills/` and the `.mjs` tests in `tests/` are the harness itself. `feature_list.json`, `PROGRESS.md`, `progress/`, `session-handoff.md` and `DECISIONS.md` record what was built, in what order and why.

## License

MIT
