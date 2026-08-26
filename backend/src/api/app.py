"""FastAPI application wiring.

This module is intentionally thin. The previous version monkey-patched
``save``/``get`` aliases onto repositories at startup (because the service and
the repositories disagreed on method names) and held a single shared aiosqlite
connection open for the whole process. Both are gone: the service and
repositories now share one vocabulary, and repositories open a short-lived
connection per operation (see :mod:`database.db`), so the app just constructs
them.

The LLM client is selected at startup: a real Gemini client when
``GEMINI_API_KEY`` is present and the SDK initialises, otherwise a deterministic
mock. Extraction is optional to the pipeline, so the mock is a first-class,
fully-supported mode — the deterministic engine does all the load-bearing work.
"""

import contextlib
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import cases, demo
from src.database.migrations import init_db
from src.database.repositories import (
    AuditRepository,
    CaseRepository,
    ClaimRepository,
    EvidenceRepository,
    TimelineRepository,
)
from src.extraction.llm_client import MockLLMClient
from src.observability.logger import get_logger, setup_logger

logger = get_logger(__name__)


def _build_llm_client():
    """Return a real Gemini client if configured, else a deterministic mock."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.info("llm_client_selected", client="MockLLMClient", reason="no GEMINI_API_KEY")
        return MockLLMClient()
    try:
        from src.extraction.llm_client import GeminiClient

        client = GeminiClient(api_key=api_key)
        logger.info("llm_client_selected", client="GeminiClient", model=client.model)
        return client
    except Exception as exc:  # noqa: BLE001 - fall back rather than fail startup
        logger.warning("gemini_init_failed_falling_back_to_mock", error=str(exc))
        return MockLLMClient()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logger()
    await init_db()
    app.state.case_service = _build_case_service()
    logger.info("app_started")
    yield


def _build_case_service():
    from src.orchestrator.case_service import CaseService

    return CaseService(
        case_repo=CaseRepository(),
        evidence_repo=EvidenceRepository(),
        claim_repo=ClaimRepository(),
        timeline_repo=TimelineRepository(),
        audit_repo=AuditRepository(),
        llm_client=_build_llm_client(),
    )


app = FastAPI(title="DisputeShield API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cases.router, prefix="/api")
app.include_router(demo.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    # Domain-level validation errors are safe to surface as 400s.
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Log the detail server-side; return a generic message so internals and
    # any embedded evidence content never leak to the client.
    logger.error("unhandled_exception", path=str(request.url.path), error=str(exc))
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})
