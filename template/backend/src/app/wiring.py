"""Builds the LLM client from settings: the only place that knows which provider is used."""

from ai_app_chassis import FakeLLMProvider, LLMClient, LLMProvider, ModelRouter

from app.settings import Settings
from app.summarize import fake_summarize


def build_client(settings: Settings) -> LLMClient:
    provider: LLMProvider
    if settings.uses_fake:
        provider = FakeLLMProvider({"summarize": fake_summarize})
    else:  # pragma: no cover - needs the litellm extra and a key
        from ai_app_chassis.litellm_provider import LiteLLMProvider

        provider = LiteLLMProvider()
    return LLMClient(provider, ModelRouter(settings.step_models, settings.default_model))
