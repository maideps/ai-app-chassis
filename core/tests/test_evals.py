import json

from ai_app_chassis import EvalCase, load_cases, run_eval


def test_run_eval_scores_cases_and_survives_a_crash(tmp_path):
    cases = [
        EvalCase("a", {"n": 1}, 2),
        EvalCase("b", {"n": 2}, 5),
        EvalCase("c", {"n": 0}, 0),
    ]

    def predict(inp):
        if inp["n"] == 0:
            raise ZeroDivisionError("boom")
        return inp["n"] * 2

    report = run_eval("double", cases, predict)
    assert report.score == round(1 / 3, 4)
    data = json.loads(report.write(tmp_path / "out" / "report.json").read_text("utf-8"))
    assert data["cases"] == 3
    assert data["errors"] == 1
    assert data["score"] == report.score
    assert data["results"][2]["error"] == "ZeroDivisionError: boom"


def test_custom_scorer_and_jsonl_loading(tmp_path):
    path = tmp_path / "golden.jsonl"
    path.write_text('{"id": 1, "input": {"q": "x"}, "expected": "x"}\n\n', encoding="utf-8")
    [case] = load_cases(path)
    assert case.id == "1"
    report = run_eval(
        "echo",
        [case],
        lambda inp: inp["q"].upper(),
        scorer=lambda out, exp: 0.5 if out.lower() == exp else 0.0,
    )
    assert report.score == 0.5


def test_an_empty_eval_scores_zero():
    assert run_eval("none", [], lambda inp: None).score == 0.0
