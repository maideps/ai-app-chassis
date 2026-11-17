"""The LiteLLM adapters against a simulated ``litellm`` module: the request each one sends and
how each reads the response. A real model is exercised by ``npm run eval:baseline`` (feat-007).
"""

import math
import sys
import types
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

from ai_app_chassis import LLMClient, Message, ModelRouter
from ai_app_chassis.litellm_provider import LiteLLMProvider
from ai_app_chassis.rag import LiteLLMEmbedder
from ai_app_chassis.rag_eval import build_embedder


class FakeLiteLLM(types.ModuleType):
    def __init__(self, reply: str | None = '{"label": "bug"}') -> None:
        super().__init__("litellm")
        self.reply = reply
        self.calls: list[dict[str, Any]] = []
        self.cost: float | Exception = 0.0012

    def completion(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        message = SimpleNamespace(content=self.reply)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=message)],
            usage=SimpleNamespace(prompt_tokens=12, completion_tokens=5),
        )

    def completion_cost(self, completion_response: Any) -> float:
        if isinstance(self.cost, Exception):
            raise self.cost
        return self.cost

    def embedding(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        # One provider style as dicts, the other as objects: the embedder reads both.
        data: list[Any] = [{"embedding": [3.0, 4.0]}, SimpleNamespace(embedding=[0.0, 2.0])]
        return SimpleNamespace(data=data[: len(kwargs["input"])])


@pytest.fixture
def litellm(monkeypatch: pytest.MonkeyPatch) -> FakeLiteLLM:
    fake = FakeLiteLLM()
    monkeypatch.setitem(sys.modules, "litellm", fake)
    return fake


class Verdict(BaseModel):
    label: str


def test_provider_sends_messages_schema_and_defaults(litellm: FakeLiteLLM) -> None:
    provider = LiteLLMProvider(max_tokens=300)
    completion = provider.complete(
        [Message("system", "be brief"), Message("user", "hi")],
        model="openai/gpt-x",
        response_schema=Verdict.model_json_schema(),
        temperature=0.2,
    )
    [call] = litellm.calls
    assert call["model"] == "openai/gpt-x"
    assert call["messages"] == [
        {"role": "system", "content": "be brief"},
        {"role": "user", "content": "hi"},
    ]
    assert call["temperature"] == 0.2
    assert call["max_tokens"] == 300
    assert call["response_format"]["type"] == "json_schema"
    assert call["response_format"]["json_schema"]["schema"]["required"] == ["label"]
    assert completion.text == '{"label": "bug"}'
    assert completion.model == "openai/gpt-x"
    assert (completion.usage.input_tokens, completion.usage.output_tokens) == (12, 5)
    assert completion.usage.cost_usd == 0.0012
    assert completion.usage.latency_ms >= 0


def test_provider_without_schema_and_with_unknown_cost(litellm: FakeLiteLLM) -> None:
    litellm.reply = None
    litellm.cost = ValueError("model not in the price map")
    completion = LiteLLMProvider().complete([Message("user", "hi")], model="x/y")
    assert "response_format" not in litellm.calls[0]
    assert completion.text == ""
    assert completion.usage.cost_usd == 0.0


def test_structured_output_works_through_the_client(litellm: FakeLiteLLM) -> None:
    client = LLMClient(LiteLLMProvider(), ModelRouter({}, "anthropic/claude-x"))
    verdict, _ = client.structured("classify", [Message("user", "crash on start")], Verdict)
    assert verdict == Verdict(label="bug")
    assert client.ledger.summary()["total"]["cost_usd"] == 0.0012


def test_embedder_normalizes_both_response_shapes(litellm: FakeLiteLLM) -> None:
    embedder = LiteLLMEmbedder("openai/text-embedding-x", dimensions=2)
    first, second = embedder.embed(["a", "b"])
    assert first == pytest.approx([0.6, 0.8])
    assert second == pytest.approx([0.0, 1.0])
    assert math.isclose(sum(x * x for x in first), 1.0)
    assert litellm.calls[0] == {
        "model": "openai/text-embedding-x",
        "input": ["a", "b"],
        "dimensions": 2,
    }
    assert isinstance(build_embedder("litellm:openai/text-embedding-x"), LiteLLMEmbedder)


def test_a_missing_litellm_install_names_the_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    # None in sys.modules makes `import litellm` raise ImportError, installed or not.
    monkeypatch.setitem(sys.modules, "litellm", None)
    with pytest.raises(RuntimeError, match=r"ai-app-chassis\[litellm\]"):
        LiteLLMProvider()
    with pytest.raises(RuntimeError, match=r"ai-app-chassis\[litellm\]"):
        LiteLLMEmbedder("any")
