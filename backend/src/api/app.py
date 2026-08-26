import contextlib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import cases, demo
from src.database.migrations import init_db
from src.database.db import get_db_connection
from src.database.repositories import (
    CaseRepository, 
    EvidenceRepository, 
    ClaimRepository, 
    TimelineRepository, 
    AuditRepository
)
from src.orchestrator.case_service import CaseService
from src.extraction.llm_client import MockLLMClient

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB
    await init_db()
    
    # Initialize CaseService
    async with get_db_connection() as db:
        case_repo = CaseRepository(db)
        evidence_repo = EvidenceRepository(db)
        claim_repo = ClaimRepository(db)
        timeline_repo = TimelineRepository(db)
        audit_repo = AuditRepository(db)
        
        # Patching repo method names if they differ from case_service expectations
        if not hasattr(case_repo, 'save'):
            case_repo.save = case_repo.create_case
        if not hasattr(case_repo, 'get'):
            case_repo.get = case_repo.get_case
        if not hasattr(evidence_repo, 'save'):
            evidence_repo.save = evidence_repo.create_evidence
        if not hasattr(evidence_repo, 'get_by_case'):
            evidence_repo.get_by_case = evidence_repo.get_evidence_by_case
        if not hasattr(claim_repo, 'save'):
            claim_repo.save = claim_repo.create_claim
        if not hasattr(timeline_repo, 'save'):
            timeline_repo.save = timeline_repo.create_event
        if not hasattr(audit_repo, 'save'):
            audit_repo.save = audit_repo.log_entry

        llm_client = MockLLMClient()
        app.state.case_service = CaseService(
            case_repo=case_repo,
            evidence_repo=evidence_repo,
            claim_repo=claim_repo,
            timeline_repo=timeline_repo,
            audit_repo=audit_repo,
            llm_client=llm_client
        )
        yield

app = FastAPI(title="DisputeShield API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cases.router, prefix="/api")
app.include_router(demo.router, prefix="/api")

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=500, content={"message": str(exc)})
