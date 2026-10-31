"""The example use case: summarize a text into one sentence and a few keywords."""

import json
import re
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ai_app_chassis import LLMClient, Message, PromptStore, check_input, redact_pii
from ai_app_chassis.guardrails import InputPolicy
from pydantic import BaseModel, Field

PROMPTS = PromptStore(Path(__file__).parent / "prompts")
STOPWORDS = {
    "about",
    "after",
    "also",
    "been",
    "from",
    "have",
    "into",
    "more",
    "that",
    "their",
    "there",
    "these",
    "they",
    "this",
    "were",
    "what",
    "when",
    "which",
    "while",
    "will",
    "with",
}


class Summary(BaseModel):
    summary: str = Field(max_length=400)
    keywords: list[str] = Field(default_factory=list, max_length=3)


def summarize(client: LLMClient, text: str, *, policy: InputPolicy | None = None) -> Summary:
    """Guardrails first (they cost nothing), then one structured call on the redacted text."""
    clean = redact_pii(check_input(text, policy))
    prompt = PROMPTS.load("summarize")
    result, _ = client.structured("summarize", prompt.render(text=clean), Summary, prompt=prompt.id)
    return result


def fake_summarize(messages: Sequence[Message], schema: dict[str, Any] | None) -> str:
    """Deterministic stand-in for a model: the first sentence plus the most frequent long words.
    Good enough to exercise the whole pipeline and the eval without a key."""
    text = messages[-1].content.split("Text:", 1)[-1].strip()
    first = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0]
    words = [w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in STOPWORDS]
    keywords = [w for w, _ in Counter(words).most_common(3)]
    return json.dumps({"summary": first[:400], "keywords": keywords})
