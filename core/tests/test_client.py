import json

import pytest
from pydantic import BaseModel

from ai_app_chassis import (
    FakeLLMProvider,
    LLMClient,
    Message,
    ModelRouter,
    StructuredOutputError,
    extract_json,
)


class Verdict(BaseModel):
    label: str
    confidence: float


def client_with(handler, *, retries: int = 1) -> LLMClient:
    provider = FakeLLMProvider({"judge": handler})
    return LLMClient(
        provider,
        ModelRouter({"classify": "fake/judge"}, default="fake/other"),
        max_validation_retries=retries,
    )


def test_router_falls_back_to_the_default_model():
    router = ModelRouter({"classify": "fake/judge"}, default="fake/other")
    assert router.model_for("classify") == "fake/judge"
    assert router.model_for("summarize") == "fake/other"


def test_structured_parses_fenced_json_and_records_the_call():
    client = client_with(lambda m, s: '```json\n{"label": "bug", "confidence": 0.9}\n```')
    verdict, completion = client.structured(
        "classify", [Message("user", "x")], Verdict, prompt="classify/v1"
    )
    assert verdict == Verdict(label="bug", confidence=0.9)
    assert completion.model == "fake/judge"
    [record] = client.ledger.records
    assert (record.step, record.prompt, record.ok) == ("classify", "classify/v1", True)


def test_structured_retries_with_the_validation_error_then_succeeds():
    replies = iter(['{"label": "bug"}', '{"label": "bug", "confidence": 0.5}'])
    seen: list[list[Message]] = []

    def handler(messages, schema):
        seen.append(list(messages))
        return next(replies)

    verdict, _ = client_with(handler).structured("classify", [Message("user", "x")], Verdict)
    assert verdict.confidence == 0.5
    assert "did not match the required JSON schema" in seen[1][-1].content


def test_structured_gives_up_after_the_retry_budget():
    client = client_with(lambda m, s: "not json", retries=1)
    with pytest.raises(StructuredOutputError):
        client.structured("classify", [Message("user", "x")], Verdict)
    assert [r.ok for r in client.ledger.records] == [False, False]


def test_unknown_fake_handler_returns_the_smallest_valid_instance():
    provider = FakeLLMProvider()
    reply = provider.complete(
        [Message("user", "x")], model="fake/anything", response_schema=Verdict.model_json_schema()
    )
    assert Verdict.model_validate(json.loads(reply.text)) == Verdict(label="", confidence=0)
    assert provider.complete([Message("user", "x")], model="fake/anything").text == "fake response"


def test_ledger_summary_totals_and_groups_by_step():
    client = client_with(lambda m, s: '{"label": "a", "confidence": 1}')
    for _ in range(3):
        client.structured("classify", [Message("user", "hello world")], Verdict)
    client.complete("summarize", [Message("user", "hi")])
    summary = client.ledger.summary()
    assert summary["total"]["calls"] == 4
    assert summary["by_step"]["classify"]["calls"] == 3
    assert summary["by_step"]["summarize"]["failed"] == 0
    assert summary["total"]["cost_usd"] == 0.0


def test_on_call_hook_sees_every_record():
    seen = []
    client = LLMClient(FakeLLMProvider(), ModelRouter({}, "fake/x"), on_call=seen.append)
    client.complete("step", [Message("user", "x")])
    assert [r.step for r in seen] == ["step"]


def test_extract_json_strips_prose_around_the_object():
    assert extract_json('Sure! {"a": 1} hope that helps') == '{"a": 1}'
