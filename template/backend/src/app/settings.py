"""Configuration from the environment. The default model is the deterministic fake, so the app
runs, tests and evaluates with no key; set APP_MODEL to a LiteLLM model name to use a real one."""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    default_model: str = "fake/summarize"
    step_models: dict[str, str] = field(default_factory=dict)
    max_input_chars: int = 8000

    @property
    def uses_fake(self) -> bool:
        models = [self.default_model, *self.step_models.values()]
        return all(m.startswith("fake/") for m in models)


def from_env() -> Settings:
    step_models = {}
    if "APP_SUMMARIZE_MODEL" in os.environ:
        step_models["summarize"] = os.environ["APP_SUMMARIZE_MODEL"]
    return Settings(
        default_model=os.environ.get("APP_MODEL", "fake/summarize"),
        step_models=step_models,
        max_input_chars=int(os.environ.get("APP_MAX_INPUT_CHARS", "8000")),
    )
