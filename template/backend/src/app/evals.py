"""Golden-set eval for summarize: keyword recall against hand-labelled keywords.

    chassis-app-eval        # writes evals/results/summarize.json and prints the score

The report's ``score`` is what the harness quality gate reads (see .harness/quality.json).
"""

from pathlib import Path
from typing import Any

from ai_app_chassis import load_cases, run_eval

from app.settings import from_env
from app.summarize import Summary, summarize
from app.wiring import build_client

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "evals" / "golden" / "summarize.jsonl"
REPORT = ROOT / "evals" / "results" / "summarize.json"


def keyword_recall(output: Summary, expected: dict[str, Any]) -> float:
    wanted = set(expected["keywords"])
    return len(set(output.keywords) & wanted) / len(wanted) if wanted else 1.0


def main() -> None:
    client = build_client(from_env())
    report = run_eval(
        "summarize",
        load_cases(GOLDEN),
        lambda inp: summarize(client, inp["text"]),
        scorer=keyword_recall,
    )
    report.write(REPORT)
    print(f"summarize: score {report.score} over {len(report.results)} cases -> {REPORT}")


if __name__ == "__main__":
    main()
