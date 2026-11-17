import sys
import types
from types import SimpleNamespace
from typing import Any

import pytest
from ai_app_chassis import FakeLLMProvider
from ai_app_chassis.litellm_provider import LiteLLMProvider

from app.settings import Settings
from app.summarize import summarize
from app.wiring import build_client


def test_fake_models_use_the_fake_provider():
    assert isinstance(build_client(Settings()).provider, FakeLLMProvider)


def test_a_real_model_goes_through_litellm(monkeypatch: pytest.MonkeyPatch):
    calls: list[dict[str, Any]] = []
    litellm = types.ModuleType("litellm")

    def completion(**kwargs: Any) -> SimpleNamespace:
        calls.append(kwargs)
        reply = '{"summary": "Sync ships.", "keywords": ["sync"]}'
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=reply))],
            usage=SimpleNamespace(prompt_tokens=30, completion_tokens=8),
        )

    litellm.completion = completion  # type: ignore[attr-defined]
    litellm.completion_cost = lambda completion_response: 0.0004  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "litellm", litellm)

    settings = Settings(default_model="fake/other", step_models={"summarize": "openai/gpt-x"})
    client = build_client(settings)
    assert isinstance(client.provider, LiteLLMProvider)
    result = summarize(client, "Sync ships today.")
    assert result.keywords == ["sync"]
    assert calls[0]["model"] == "openai/gpt-x"
    assert client.ledger.summary()["total"]["cost_usd"] == 0.0004
