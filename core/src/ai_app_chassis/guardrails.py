"""Cheap checks around a model call: reject what should never reach the model, and redact
personal data before it does. They are deterministic on purpose, so they can be tested and
never cost a model call."""

import re
from dataclasses import dataclass

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{7,}\d(?!\w)")
INJECTION = re.compile(
    r"ignore (?:all |any )?(?:previous|prior|above) instructions|reveal (?:your|the) system prompt",
    re.IGNORECASE,
)


class GuardrailViolation(ValueError):
    def __init__(self, rule: str, detail: str) -> None:
        super().__init__(f"{rule}: {detail}")
        self.rule = rule


@dataclass(frozen=True)
class InputPolicy:
    max_chars: int = 8000
    block_injection: bool = True


def check_input(text: str, policy: InputPolicy | None = None) -> str:
    """Return the text unchanged when it may go to a model; raise GuardrailViolation if not."""
    policy = policy or InputPolicy()
    if not text.strip():
        raise GuardrailViolation("empty_input", "the input is empty")
    if len(text) > policy.max_chars:
        raise GuardrailViolation("too_long", f"{len(text)} characters > {policy.max_chars}")
    if policy.block_injection and INJECTION.search(text):
        raise GuardrailViolation("prompt_injection", "the input tries to override instructions")
    return text


def redact_pii(text: str) -> str:
    """Replace e-mail addresses and phone numbers with placeholders."""
    return PHONE.sub("[phone]", EMAIL.sub("[email]", text))
