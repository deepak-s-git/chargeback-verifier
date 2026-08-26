from typing import List, Dict, Any
from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from src.domain.models import CaseCreateRequest
from src.domain.enums import CaseStatus
from src.verification.requirement_engine import evaluate_requirements
from src.verification.timeline_builder import build_timeline
from src.verification.contradiction import detect_contradictions
from src.scoring.scorer import score_evidence
from src.orchestrator.gate import apply_gate
from src.domain.rules import get_requirements

router = APIRouter(prefix='/cases', tags=['cases'])

@router.post('/', response_model=dict)
async def create_case(request: Request, body: CaseCreateRequest):
    case_service = request.app.state.case_service
    case = await case_service.create_case(body)
    return case.model_dump()

@router.get('/', response_model=List[dict])
async def list_cases(request: Request):
    case_service = request.app.state.case_service
    cases = await case_service.case_repo.list_cases()
    return [c.model_dump() for c in cases]

@router.get('/{case_id}', response_model=dict)
async def get_case(request: Request, case_id: str):
    case_service = request.app.state.case_service
    case = await case_service.case_repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    evidence = await case_service.evidence_repo.get_evidence_by_case(case_id)
    case_data = case.model_dump()
    case_data['evidence_items'] = [e.model_dump() for e in evidence]
    return case_data

@router.post('/{case_id}/evidence')
async def upload_evidence(request: Request, case_id: str, file: UploadFile = File(...)):
    case_service = request.app.state.case_service
    content = await file.read()
    try:
        items = await case_service.add_evidence(
            case_id=case_id,
            file_path=file.filename,
            file_content=content,
            mime_type=file.content_type
        )
        return {"items": [item.model_dump() for item in items]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post('/{case_id}/analyze', response_model=dict)
async def analyze_case(request: Request, case_id: str):
    case_service = request.app.state.case_service
    try:
        # We can just call analyze_case since we know it's implemented in CaseService
        analysis = await case_service.analyze_case(case_id)
        
        # Format the result to match the API response
        return {
            "case_id": case_id,
            "score": analysis.score.model_dump(),
            "claims": [c.model_dump() for c in analysis.claims],
            "requirements": [r.model_dump() for r in analysis.requirements],
            "contradictions": [c.model_dump() for c in analysis.contradictions],
            "timeline": [t.model_dump() for t in analysis.timeline],
            "summary": ["Analysis complete", f"Gate Status: {analysis.gate_result.gate_status}"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/{case_id}/analysis', response_model=dict)
async def get_analysis(request: Request, case_id: str):
    case_service = request.app.state.case_service
    case = await case_service.case_repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Normally we would fetch the persisted analysis. For now we just rerun it or return stub.
    return await analyze_case(request, case_id)

@router.get('/{case_id}/timeline', response_model=List[dict])
async def get_timeline(request: Request, case_id: str):
    case_service = request.app.state.case_service
    timeline = await case_service.timeline_repo.get_timeline_by_case(case_id)
    return [t.model_dump() for t in timeline]

@router.get('/{case_id}/package', response_model=dict)
async def get_package(request: Request, case_id: str):
    case_service = request.app.state.case_service
    case = await case_service.case_repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Check if package exists in case
    if case.package:
        return case.package.model_dump()
        
    try:
        package = await case_service.generate_package(case_id)
        return package.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/{case_id}/audit', response_model=List[dict])
async def get_audit_trail(request: Request, case_id: str):
    case_service = request.app.state.case_service
    audit_trail = await case_service.audit_repo.get_audit_trail(case_id)
    return [a.model_dump() for a in audit_trail]
