"""ai-app-chassis: runtime building blocks for LLM-backed apps."""

from ai_app_chassis.client import (
    CallLedger,
    CallRecord,
    LLMClient,
    ModelRouter,
    StructuredOutputError,
    extract_json,
)
from ai_app_chassis.evals import (
    CaseResult,
    EvalCase,
    EvalReport,
    exact_match,
    load_cases,
    run_eval,
)
from ai_app_chassis.fake import FakeHandler, FakeLLMProvider, minimal_instance
from ai_app_chassis.guardrails import GuardrailViolation, InputPolicy, check_input, redact_pii
from ai_app_chassis.llm import Completion, LLMProvider, Message, Usage
from ai_app_chassis.prompts import Prompt, PromptNotFoundError, PromptStore

__all__ = [
    "CallLedger",
    "CallRecord",
    "CaseResult",
    "Completion",
    "EvalCase",
    "EvalReport",
    "FakeHandler",
    "FakeLLMProvider",
    "GuardrailViolation",
    "InputPolicy",
    "LLMClient",
    "LLMProvider",
    "Message",
    "ModelRouter",
    "Prompt",
    "PromptNotFoundError",
    "PromptStore",
    "StructuredOutputError",
    "Usage",
    "check_input",
    "exact_match",
    "extract_json",
    "load_cases",
    "minimal_instance",
    "redact_pii",
    "run_eval",
]
