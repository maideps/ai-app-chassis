# Quality Document

Rate each module on a scale of A (excellent) / B (good) / C (acceptable) / D (needs work) / F (failing).

## Modules

| Module | Test Coverage | Type Safety | Documentation | Arch Compliance | Performance |
|---|---|---|---|---|---|
| core: llm, fake, client | A | A | B | A | B |
| core: prompts, guardrails, evals | A | A | B | A | B |
| core: rag, rag_eval | A | A | B | A | C |
| core: litellm_provider | B | A | B | A | n/a |
| template/backend app | A | A | B | A | B |

## Summary

- **Overall Quality Grade:** B
- **Blockers:** none
- **Areas requiring attention:** `litellm_provider` and `LiteLLMEmbedder` are tested against a simulated litellm module but have never run against a real model; the eval scores only reflect the fake summarizer and the lexical hashing embedder; `InMemoryVectorStore` is a brute-force scan (performance C beyond a few thousand chunks).

## Notes

- Coverage 93.61 % and eval score 1.0 on 2026-10-30, both on the fake model.

---

_Update this document at session close for modules touched in the session._
