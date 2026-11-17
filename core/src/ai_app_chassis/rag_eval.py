"""Retrieval eval: index a folder of documents and score recall@k on a golden set.

    python -m ai_app_chassis.rag_eval --docs DIR --golden FILE.jsonl --out REPORT.json [--k 3]
                                      [--embedder hashing | litellm:<model>]

Each document is a ``.md`` or ``.txt`` file whose name (without extension) is its id. Each
golden line is ``{"id", "input": {"query"}, "expected": {"relevant": [doc ids]}}``. The
report's ``score`` is the mean recall@k, which a harness quality gate reads; ``mrr`` is added
next to it.
"""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ai_app_chassis.evals import EvalReport, load_cases, run_eval
from ai_app_chassis.rag import (
    Embedder,
    HashingEmbedder,
    LiteLLMEmbedder,
    Retriever,
    recall_at_k,
    reciprocal_rank,
)


def load_documents(folder: Path | str) -> dict[str, str]:
    files = sorted(p for p in Path(folder).iterdir() if p.suffix in {".md", ".txt"})
    return {p.stem: p.read_text(encoding="utf-8") for p in files}


def build_embedder(spec: str) -> Embedder:
    if spec == "hashing":
        return HashingEmbedder()
    if spec.startswith("litellm:"):  # pragma: no cover - needs the extra and a key
        return LiteLLMEmbedder(spec.split(":", 1)[1])
    raise ValueError(f"unknown embedder {spec!r}: use 'hashing' or 'litellm:<model>'")


def evaluate(
    documents: dict[str, str], golden: Path | str, *, embedder: Embedder, k: int
) -> EvalReport:
    retriever = Retriever(embedder)
    retriever.index(documents)
    return run_eval(
        "retrieval",
        load_cases(golden),
        lambda inp: retriever.retrieve_documents(inp["query"], k),
        scorer=lambda ranked, expected: recall_at_k(ranked, expected["relevant"], k),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--docs", required=True)
    parser.add_argument("--golden", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--embedder", default="hashing")
    args = parser.parse_args(argv)

    golden = load_cases(args.golden)
    report = evaluate(
        load_documents(args.docs), args.golden, embedder=build_embedder(args.embedder), k=args.k
    )
    data: dict[str, Any] = report.to_dict()
    expected = {case.id: case.expected["relevant"] for case in golden}
    ranks = [reciprocal_rank(r.output or [], expected[r.id]) for r in report.results]
    data.update(k=args.k, embedder=args.embedder, mrr=round(sum(ranks) / max(len(ranks), 1), 4))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(
        f"retrieval: recall@{args.k} {report.score}, mrr {data['mrr']} over {len(golden)} queries"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
