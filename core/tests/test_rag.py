import math

import pytest

from ai_app_chassis import (
    Chunk,
    HashingEmbedder,
    InMemoryVectorStore,
    Retriever,
    chunk_text,
    recall_at_k,
    reciprocal_rank,
)


def test_chunk_text_packs_paragraphs_up_to_the_limit():
    text = "First paragraph.\n\nSecond paragraph.\n\n\n" + "x" * 30
    chunks = chunk_text(text, "doc", max_chars=40, overlap=5)
    assert [c.id for c in chunks] == ["doc#0", "doc#1"]
    assert chunks[0].text == "First paragraph.\n\nSecond paragraph."
    assert chunks[1].text == "x" * 30
    assert all(c.doc_id == "doc" for c in chunks)


def test_a_long_paragraph_is_cut_into_overlapping_windows():
    paragraph = "".join(chr(ord("a") + i % 26) for i in range(100))
    chunks = chunk_text(paragraph, "long", max_chars=40, overlap=10)
    assert [len(c.text) for c in chunks] == [40, 40, 40]
    assert chunks[0].text[-10:] == chunks[1].text[:10]
    assert "".join(c.text[10:] if i else c.text for i, c in enumerate(chunks)) == paragraph


def test_chunk_text_rejects_an_overlap_as_large_as_the_chunk():
    with pytest.raises(ValueError):
        chunk_text("text", "d", max_chars=10, overlap=10)
    assert chunk_text("  \n\n  ", "empty") == []


def test_hashing_embedder_is_deterministic_normalized_and_lexical():
    embedder = HashingEmbedder(dimension=256)
    a, b, c, empty = embedder.embed(
        ["Rotate the API token", "rotate the api TOKEN!", "Export billing data", "the of and"]
    )
    assert a == b
    assert math.isclose(sum(x * x for x in a), 1.0)
    assert sum(x * y for x, y in zip(a, c, strict=True)) < 0.5
    assert not any(empty)


def test_vector_store_ranks_by_cosine_and_skips_unrelated_chunks():
    store = InMemoryVectorStore()
    chunks = [Chunk("a#0", "a", "x"), Chunk("b#0", "b", "y"), Chunk("c#0", "c", "z")]
    store.add(chunks, [[1.0, 0.0], [0.6, 0.8], [0.0, 1.0]])
    assert len(store) == 3
    assert [s.chunk.id for s in store.search([1.0, 0.1], k=2)] == ["a#0", "b#0"]
    assert [s.chunk.id for s in store.search([-1.0, 0.0], k=3)] == []
    assert store.search([0.0, 0.0], k=3) == []
    with pytest.raises(ValueError):
        store.add(chunks, [[1.0, 0.0]])


def test_retriever_finds_the_document_that_shares_the_words():
    retriever = Retriever(HashingEmbedder())
    added = retriever.index(
        {
            "tokens": "API tokens expire after 30 days. Rotate a token from the settings page.",
            "billing": "Invoices are sent on the first day of the month. Billing data is exported.",
            "cache": "The cache lives in the user folder. Clear the cache with the purge command.",
        }
    )
    assert added == 3
    assert retriever.retrieve_documents("how do I rotate my API token", k=2)[0] == "tokens"
    assert retriever.retrieve_documents("clear the cache", k=1) == ["cache"]
    hits = retriever.retrieve("monthly invoices", k=1)
    assert hits[0].chunk.doc_id == "billing"
    assert 0 < hits[0].score <= 1
    assert Retriever(HashingEmbedder()).index({}) == 0


def test_retrieve_documents_deduplicates_chunks_of_one_document():
    retriever = Retriever(HashingEmbedder(), max_chars=40, overlap=5)
    retriever.index({"long": "token rotation. " * 10, "other": "token expiry rules"})
    assert retriever.retrieve_documents("token", k=5) == ["long", "other"]


def test_retrieval_metrics():
    ranked = ["b", "a", "c"]
    assert recall_at_k(ranked, ["a", "d"], k=2) == 0.5
    assert recall_at_k(ranked, ["c"], k=2) == 0.0
    assert recall_at_k(ranked, [], k=2) == 1.0
    assert reciprocal_rank(ranked, ["a"]) == 0.5
    assert reciprocal_rank(ranked, ["z"]) == 0.0
