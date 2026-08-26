import uuid
from typing import List, Optional

from pydantic import BaseModel

from src.domain.models import (
    DisputeCase, CaseCreateRequest, EvidenceItem, 
    Requirement, TimelineEvent, Contradiction, EvidenceScore, Claim,
    AuditLogEntry, EvidencePackage
)
from src.domain.enums import CaseStatus, ClaimStatus, Recommendation
from src.domain.rules import get_requirements
from src.ingestion.pipeline import ingest_evidence_file
from src.extraction.extractor import EvidenceExtractor
from src.extraction.llm_client import LLMClient
from src.verification.requirement_engine import evaluate_requirements
from src.verification.timeline_builder import build_timeline
from src.verification.ce30_matcher import evaluate_ce30, CE30Result
from src.verification.contradiction import detect_contradictions
from src.verification.claim_verifier import verify_claim
from src.scoring.scorer import score_evidence
from src.database.repositories import CaseRepository, EvidenceRepository, ClaimRepository, TimelineRepository, AuditRepository
from src.security.injection import detect_injection
from src.orchestrator.gate import apply_gate, GateResult
from src.observability.logger import get_logger

logger = get_logger(__name__)

class CaseAnalysisResult(BaseModel):
    case: DisputeCase
    evidence: List[EvidenceItem]
    requirements: List[Requirement]
    timeline: List[TimelineEvent]
    ce30_result: Optional[CE30Result]
    contradictions: List[Contradiction]
    claims: List[Claim]
    score: EvidenceScore
    gate_result: GateResult

class CaseService:
    def __init__(
        self, 
        case_repo: CaseRepository,
        evidence_repo: EvidenceRepository,
        claim_repo: ClaimRepository,
        timeline_repo: TimelineRepository,
        audit_repo: AuditRepository,
        llm_client: LLMClient
    ):
        self.case_repo = case_repo
        self.evidence_repo = evidence_repo
        self.claim_repo = claim_repo
        self.timeline_repo = timeline_repo
        self.audit_repo = audit_repo
        self.extractor = EvidenceExtractor(llm_client)

    async def create_case(self, request: CaseCreateRequest) -> DisputeCase:
        case = DisputeCase(
            merchant_id=request.merchant_id,
            transaction_id=request.transaction_id,
            network=request.network,
            reason_code=request.reason_code,
            amount=request.amount,
            currency=request.currency,
            status=CaseStatus.OPEN
        )
        await self.case_repo.save(case)
        await self.audit_repo.save(AuditLogEntry(
            id=f"audit_{uuid.uuid4().hex[:8]}",
            case_id=case.id,
            pipeline_stage="INITIALIZATION",
            model_used="system",
            decision="CASE_CREATED",
            confidence=1.0,
            latency_ms=0
        ))
        logger.info(f"Case {case.id} created.")
        return case
        
    async def add_evidence(self, case_id: str, file_path: str, file_content: bytes, mime_type: str) -> List[EvidenceItem]:
        # 1 & 2. Validate and Check for prompt injection
        content_str = file_content.decode(errors='ignore')
        injection_result = detect_injection(content_str)
        if injection_result.detected:
            logger.warning(f"Prompt injection detected in file {file_path}: {injection_result.patterns_matched}")
            # Don't raise - flag it but continue processing (evidence is data, not instructions)
            
        # 3. Run ingestion pipeline
        evidence_items = ingest_evidence_file(file_path, file_content, mime_type, case_id)
        
        # 4 & 5. Run AI extraction and save
        results = []
        for item in evidence_items:
            if item.content:
                extraction = await self.extractor.extract(item.content, item.source_type)
                facts = self.extractor.to_extracted_facts(extraction, item.id)
                item.extracted_facts.extend(facts)
            
            await self.evidence_repo.save(item)
            results.append(item)
            
        await self.audit_repo.save(AuditLogEntry(
            id=f"audit_{uuid.uuid4().hex[:8]}",
            case_id=case_id,
            pipeline_stage="INGESTION",
            model_used="system",
            decision="EVIDENCE_ADDED",
            confidence=1.0,
            latency_ms=0
        ))
        return results
        
    async def analyze_case(self, case_id: str) -> CaseAnalysisResult:
        case = await self.case_repo.get(case_id)
        evidence_items = await self.evidence_repo.get_by_case(case_id)
        
        req_defs = get_requirements(case.network, case.reason_code)
        
        timeline = build_timeline(evidence_items)
        requirements = evaluate_requirements(case, evidence_items, req_defs)
        
        ce30_result = None
        if case.network.value == "VISA":
            ce30_result = evaluate_ce30(case, evidence_items)
            
        contradictions = detect_contradictions(evidence_items, timeline)
        score = score_evidence(requirements, ce30_result, contradictions)
        
        claims = []
        for req in requirements:
            if req.status == RequirementStatus.SATISFIED:
                claim = Claim(
                    id=f"clm_{uuid.uuid4().hex[:8]}",
                    case_id=case_id,
                    description=f"Requirement {req.name} is satisfied",
                    status=ClaimStatus.VERIFIED,
                    supporting_evidence_ids=req.satisfying_evidence_ids,
                    provenance=None
                )
                verified_claim = verify_claim(claim, evidence_items)
                claims.append(verified_claim)
                await self.claim_repo.save(verified_claim)
                
        gate_result = apply_gate(score, contradictions, claims)
        
        case.status = CaseStatus.REVIEW_REQUIRED if gate_result.gate_status != "READY" else CaseStatus.PACKAGE_READY
        await self.case_repo.save(case)
        
        await self.audit_repo.save(AuditLogEntry(
            id=f"audit_{uuid.uuid4().hex[:8]}",
            case_id=case_id,
            pipeline_stage="VERIFICATION",
            model_used="system",
            decision=gate_result.gate_status,
            confidence=score.total_score / 100.0,
            latency_ms=0
        ))
        
        return CaseAnalysisResult(
            case=case,
            evidence=evidence_items,
            requirements=requirements,
            timeline=timeline,
            ce30_result=ce30_result,
            contradictions=contradictions,
            claims=claims,
            score=score,
            gate_result=gate_result
        )

    async def generate_package(self, case_id: str) -> EvidencePackage:
        analysis = await self.analyze_case(case_id)
        
        from src.packaging.builder import build_evidence_package
        package = build_evidence_package(analysis.case, analysis)
        
        analysis.case.status = CaseStatus.PACKAGE_READY
        await self.case_repo.save(analysis.case)
        
        await self.audit_repo.save(AuditLogEntry(
            id=f"audit_{uuid.uuid4().hex[:8]}",
            case_id=case_id,
            pipeline_stage="PACKAGING",
            model_used="llm",
            decision="PACKAGE_GENERATED",
            confidence=1.0,
            latency_ms=0
        ))
        
        return package
