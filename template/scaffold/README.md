# {{name}}

An LLM-backed service built on [ai-app-chassis](https://github.com/maideps/ai-app-chassis). It starts as the chassis example: a summarize endpoint with guardrails, structured output, a cost ledger and a golden-set eval. Replace that with this project's own use case.

See the [Harness Command Reference](docs/HARNESS.md) for every make target and npm script.

## Run it in five minutes

Needs Node 18+ and Python 3.11+.

```bash
npm run setup:python      # creates .venv and installs backend/ with its dev tools
npm run check             # lint, types, tests, build, then the quality gates
npm run eval              # golden-set eval, report in backend/evals/results/
```

Run the API on the fake model from `backend/`: `python -m uvicorn {{package}}.main:app --reload` (with the `.venv` interpreter). Set `APP_MODEL` to a LiteLLM model name to use a real model.

## Next steps

1. Replace `backend/src/{{package}}/summarize.py` with the real use case: a Pydantic output model, a prompt folder under `prompts/`, a fake handler.
2. Write golden cases in `backend/evals/golden/` and point the eval gate in `.harness/quality.json` at the new report.
3. Describe the product in `docs/PRODUCT.md` and declare features in `feature_list.json`.
