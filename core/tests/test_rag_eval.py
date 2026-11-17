import json

import pytest

from ai_app_chassis import HashingEmbedder
from ai_app_chassis.rag_eval import build_embedder, evaluate, load_documents, main


def write_corpus(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "tokens.md").write_text("Rotate the API token from the settings page.", "utf-8")
    (docs / "billing.md").write_text(
        "Invoices are issued monthly and list the VAT number.", "utf-8"
    )
    (docs / "notes.json").write_text("{}", "utf-8")  # not a document: ignored
    golden = tmp_path / "golden.jsonl"
    lines = [
        {"id": "q1", "input": {"query": "rotate my token"}, "expected": {"relevant": ["tokens"]}},
        {"id": "q2", "input": {"query": "VAT on invoices"}, "expected": {"relevant": ["billing"]}},
        {"id": "q3", "input": {"query": "unrelated words"}, "expected": {"relevant": ["billing"]}},
    ]
    golden.write_text("\n".join(json.dumps(line) for line in lines) + "\n", "utf-8")
    return docs, golden


def test_load_documents_reads_markdown_and_text_by_file_stem(tmp_path):
    docs, _ = write_corpus(tmp_path)
    assert sorted(load_documents(docs)) == ["billing", "tokens"]


def test_evaluate_scores_recall_at_k(tmp_path):
    docs, golden = write_corpus(tmp_path)
    report = evaluate(load_documents(docs), golden, embedder=HashingEmbedder(), k=1)
    assert [r.score for r in report.results] == [1.0, 1.0, 0.0]
    assert report.score == round(2 / 3, 4)


def test_main_writes_a_report_with_recall_and_mrr(tmp_path, capsys):
    docs, golden = write_corpus(tmp_path)
    out = tmp_path / "results" / "retrieval.json"
    assert main(["--docs", str(docs), "--golden", str(golden), "--out", str(out), "--k", "2"]) == 0
    data = json.loads(out.read_text("utf-8"))
    assert (data["k"], data["embedder"], data["cases"]) == (2, "hashing", 3)
    assert data["score"] == round(2 / 3, 4)
    assert data["mrr"] == round(2 / 3, 4)
    assert "recall@2" in capsys.readouterr().out


def test_build_embedder_rejects_unknown_names():
    assert isinstance(build_embedder("hashing"), HashingEmbedder)
    with pytest.raises(ValueError, match="unknown embedder"):
        build_embedder("word2vec")
