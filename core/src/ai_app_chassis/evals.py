"""Golden-set evaluation: run a predictor over labelled cases, score it, and write a JSON
report whose ``score`` a harness quality gate can read (``"path": "score"``)."""

import json
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EvalCase:
    id: str
    input: dict[str, Any]
    expected: Any


@dataclass(frozen=True)
class CaseResult:
    id: str
    score: float
    output: Any
    error: str | None = None


@dataclass
class EvalReport:
    name: str
    results: list[CaseResult] = field(default_factory=list)

    @property
    def score(self) -> float:
        """Mean case score in [0, 1]; a case that raised scores 0."""
        if not self.results:
            return 0.0
        return round(sum(r.score for r in self.results) / len(self.results), 4)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "cases": len(self.results),
            "errors": sum(1 for r in self.results if r.error),
            "score": self.score,
            "results": [{**asdict(r), "output": _jsonable(r.output)} for r in self.results],
        }

    def write(self, path: Path | str) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2, default=str) + "\n", "utf-8")
        return target


def _jsonable(output: Any) -> Any:
    """Pydantic models (the usual structured output) are stored as their fields, not repr()."""
    dump = getattr(output, "model_dump", None)
    return dump(mode="json") if callable(dump) else output


def load_cases(path: Path | str) -> list[EvalCase]:
    """Read a JSONL file of ``{"id", "input", "expected"}`` objects."""
    cases = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            raw = json.loads(line)
            cases.append(EvalCase(id=str(raw["id"]), input=raw["input"], expected=raw["expected"]))
    return cases


def exact_match(output: Any, expected: Any) -> float:
    return 1.0 if output == expected else 0.0


def run_eval(
    name: str,
    cases: Iterable[EvalCase],
    predict: Callable[[dict[str, Any]], Any],
    scorer: Callable[[Any, Any], float] = exact_match,
) -> EvalReport:
    report = EvalReport(name=name)
    for case in cases:
        try:
            output = predict(case.input)
        except Exception as exc:  # one broken case must not hide the others
            report.results.append(CaseResult(case.id, 0.0, None, f"{type(exc).__name__}: {exc}"))
            continue
        report.results.append(CaseResult(case.id, float(scorer(output, case.expected)), output))
    return report
