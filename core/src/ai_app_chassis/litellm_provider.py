"""Real models through LiteLLM (install the ``litellm`` extra). Imported lazily, so the core
and every test run without it."""

import time
from collections.abc import Sequence
from typing import Any

from ai_app_chassis.llm import Completion, Message, Usage


class LiteLLMProvider:
    def __init__(self, **defaults: Any) -> None:
        try:
            import litellm
        except ImportError as exc:  # pragma: no cover - depends on the optional extra
            raise RuntimeError(
                "LiteLLMProvider needs the litellm extra: pip install 'ai-app-chassis[litellm]'"
            ) from exc
        self._litellm = litellm
        self._defaults = defaults

    def complete(
        self,
        messages: Sequence[Message],
        *,
        model: str,
        response_schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
    ) -> Completion:  # pragma: no cover - needs a real model and key
        kwargs: dict[str, Any] = {**self._defaults, "temperature": temperature}
        if response_schema is not None:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "response", "schema": response_schema},
            }
        start = time.perf_counter()
        response = self._litellm.completion(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            **kwargs,
        )
        latency_ms = round((time.perf_counter() - start) * 1000, 3)
        usage = response.usage
        try:
            cost = float(self._litellm.completion_cost(completion_response=response))
        except Exception:
            cost = 0.0
        return Completion(
            text=response.choices[0].message.content or "",
            model=model,
            usage=Usage(
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
            ),
        )
