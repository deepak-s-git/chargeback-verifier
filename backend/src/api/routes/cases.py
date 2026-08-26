"""Case API routes.

Thin HTTP surface over :class:`CaseService`. The analysis endpoints return the
full, explainable result — score with factors, requirement coverage, claims and
their grounding status, contradictions, the reconstructed timeline, the CE 3.0
verdict, any prompt-injection finding, and the human-review gate decision — so
the frontend never has to re-derive anything the engine already computed.
"""

from typing import List

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from src.domain.models import CaseCreateRequest

router = APIRouter(prefix="/cases", tags=["cases"])


def _analysis_payload(analysis) -> dict:
    return {
        "case_id": analysis.case.id,
        "status": analysis.case.status.value,
        "score": analysis.score.model_dump(),
        "recommendation": analysis.score.recommendation.value,
        "gate_status": analysis.gate_result.gate_status.value,
        "gate_reasons": analysis.gate_result.reasons,
        "requirements": [r.model_dump() for r in analysis.requirements],
        "claims": [c.model_dump() for c in analysis.claims],
        "contradictions": [c.model_dump() for c in analysis.contradictions],
        "timeline": [t.model_dump() for t in analysis.timeline],
        "ce30": analysis.ce30_result.model_dump() if analysis.ce30_result else None,
        "injection_detected": analysis.injection_detected,
        "injection_patterns": analysis.injection_patterns,
    }


@router.post("/", response_model=dict)
async def create_case(request: Request, body: CaseCreateRequest):
    case_service = request.app.state.case_service
    case = await case_service.create_case(body)
    return case.model_dump()


@router.get("/", response_model=List[dict])
async def list_cases(request: Request):
    case_service = request.app.state.case_service
    cases = await case_service.case_repo.list_cases()
    return [c.model_dump() for c in cases]


@router.get("/{case_id}", response_model=dict)
async def get_case(request: Request, case_id: str):
    case_service = request.app.state.case_service
    case = await case_service.case_repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    evidence = await case_service.evidence_repo.get_evidence_by_case(case_id)
    case_data = case.model_dump()
    case_data["evidence_items"] = [e.model_dump() for e in evidence]
    return case_data


@router.post("/{case_id}/evidence")
async def upload_evidence(request: Request, case_id: str, file: UploadFile = File(...)):
    case_service = request.app.state.case_service
    case = await case_service.case_repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    content = await file.read()
    try:
        items = await case_service.add_evidence(
            case_id=case_id,
            file_path=file.filename or "upload.bin",
            file_content=content,
            mime_type=file.content_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"items": [item.model_dump() for item in items]}


@router.post("/{case_id}/analyze", response_model=dict)
async def analyze_case(request: Request, case_id: str):
    case_service = request.app.state.case_service
    case = await case_service.case_repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    analysis = await case_service.analyze_case(case_id)
    return _analysis_payload(analysis)


@router.get("/{case_id}/analysis", response_model=dict)
async def get_analysis(request: Request, case_id: str):
    return await analyze_case(request, case_id)


@router.get("/{case_id}/timeline", response_model=List[dict])
async def get_timeline(request: Request, case_id: str):
    case_service = request.app.state.case_service
    timeline = await case_service.timeline_repo.get_timeline_by_case(case_id)
    return [t.model_dump() for t in timeline]


@router.get("/{case_id}/package", response_model=dict)
async def get_package(request: Request, case_id: str):
    case_service = request.app.state.case_service
    case = await case_service.case_repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    package = await case_service.generate_package(case_id)
    return package.model_dump()


@router.get("/{case_id}/audit", response_model=List[dict])
async def get_audit_trail(request: Request, case_id: str):
    case_service = request.app.state.case_service
    audit_trail = await case_service.audit_repo.get_audit_trail(case_id)
    return [a.model_dump() for a in audit_trail]
