"""HTTP API: run with ``uvicorn app.main:app --reload`` from template/backend."""

from typing import Any

from ai_app_chassis import GuardrailViolation, LLMClient, StructuredOutputError
from ai_app_chassis.guardrails import InputPolicy
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.settings import Settings, from_env
from app.summarize import Summary, summarize
from app.wiring import build_client


class SummarizeRequest(BaseModel):
    text: str


def create_app(settings: Settings | None = None, client: LLMClient | None = None) -> FastAPI:
    settings = settings or from_env()
    llm = client or build_client(settings)
    policy = InputPolicy(max_chars=settings.max_input_chars)
    app = FastAPI(title="chassis-app")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "model": settings.default_model}

    @app.post("/summarize")
    def summarize_endpoint(request: SummarizeRequest) -> Summary:
        try:
            return summarize(llm, request.text, policy=policy)
        except GuardrailViolation as exc:
            violation = {"rule": exc.rule, "message": str(exc)}
            raise HTTPException(status_code=422, detail=violation) from exc
        except StructuredOutputError as exc:
            message = "the model did not return a valid summary"
            raise HTTPException(status_code=502, detail=message) from exc

    @app.get("/usage")
    def usage() -> dict[str, Any]:
        """Tokens, cost and latency of every model call since the process started."""
        return llm.ledger.summary()

    return app


app = create_app()
