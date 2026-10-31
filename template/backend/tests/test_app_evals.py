import json

from app import evals
from app.settings import Settings
from app.summarize import Summary


def test_keyword_recall():
    output = Summary(summary="s", keywords=["sync", "drafts", "device"])
    assert evals.keyword_recall(output, {"keywords": ["sync", "offline"]}) == 0.5
    assert evals.keyword_recall(output, {"keywords": []}) == 1.0


def test_settings_know_when_only_the_fake_is_used():
    assert Settings().uses_fake
    assert not Settings(step_models={"summarize": "openai/gpt-4o-mini"}).uses_fake


def test_eval_writes_a_report_the_quality_gate_can_read(tmp_path, monkeypatch, capsys):
    report = tmp_path / "summarize.json"
    monkeypatch.setattr(evals, "REPORT", report)
    evals.main()
    data = json.loads(report.read_text("utf-8"))
    assert data["cases"] == 5
    assert data["errors"] == 0
    assert 0.0 <= data["score"] <= 1.0
    assert isinstance(data["results"][0]["output"]["keywords"], list)
    assert "summarize: score" in capsys.readouterr().out
