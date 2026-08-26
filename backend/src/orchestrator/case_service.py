"""Case orchestration.

The :class:`CaseService` owns the I/O around analysis: it reads a case and its
evidence from the repositories, delegates the entire deterministic decision to
the pure :func:`~src.orchestrator.analysis.analyze_evidence` core, then persists
the result idempotently. Keeping the decision logic in one pure function means
the offline evaluation harness exercises the *same* code the API does — there is
no second, drifting implementation.

This replaces a version riddled with guaranteed crashes (an unimported
``RequirementStatus``, claims built with invalid keyword arguments, a reference
to a non-existent ``satisfying_evidence_ids`` field, and calls to repository
methods that did not exist).
"""

from typing import List, Optional

from src.database.repositories import (
    AuditRepository,
    CaseRepository,
    ClaimRepository,
    EvidenceRepository,
    TimelineRepository,
)
from src.domain.enums import CaseStatus
from src.domain.models import (
    AuditLogEntry,
    CaseCreateRequest,
    DisputeCase,
    EvidenceItem,
    EvidencePackage,
    now_utc,
)
from src.extraction.extractor import EvidenceExtractor
from src.extraction.llm_client import LLMClient
from src.ingestion.pipeline import ingest_evidence_file
from src.observability.logger import get_logger
from src.orchestrator.analysis import CaseAnalysisResult, analyze_evidence
from src.orchestrator.gate import GateStatus
from src.security.injection import detect_injection
from src.security.validators import validate_file

logger = get_logger(__name__)

# Re-exported for backwards compatibility: callers and type hints that import
# CaseAnalysisResult from the service keep working now that it lives in analysis.
__all__ = ["CaseService", "CaseAnalysisResult"]


class CaseService:
    def __init__(
        self,
        case_repo: CaseRepository,
        evidence_repo: EvidenceRepository,
        claim_repo: ClaimRepository,
        timeline_repo: TimelineRepository,
        audit_repo: AuditRepository,
        llm_client: LLMClient,
    ):
        self.case_repo = case_repo
        self.evidence_repo = evidence_repo
        self.claim_repo = claim_repo
        self.timeline_repo = timeline_repo
        self.audit_repo = audit_repo
        self.extractor = EvidenceExtractor(llm_client)
        self.llm_model_name = getattr(llm_client, "model", llm_client.__class__.__name__)

    async def _audit(
        self, case_id: str, stage: str, decision: str, confidence: float, model: str = "system"
    ) -> None:
        await self.audit_repo.log_entry(
            AuditLogEntry(
                case_id=case_id,
                pipeline_stage=stage,
                model_used=model,
                decision=decision,
                confidence=confidence,
                latency_ms=0,
            )
        )

    async def create_case(self, request: CaseCreateRequest) -> DisputeCase:
        case = DisputeCase(
            merchant_id=request.merchant_id,
            transaction_id=request.transaction_id,
            dispute_id=request.dispute_id,
            network=request.network,
            reason_code=request.reason_code,
            amount=request.amount,
            currency=request.currency,
            transaction_date=request.transaction_date,
            respond_by=request.respond_by,
            status=CaseStatus.OPEN,
        )
        await self.case_repo.create_case(case)
        await self._audit(case.id, "INITIALIZATION", "CASE_CREATED", 1.0)
        logger.info("case_created", case_id=case.id, network=case.network.value, reason_code=case.reason_code)
        return case

    async def add_evidence(
        self, case_id: str, file_path: str, file_content: bytes, mime_type: Optional[str]
    ) -> List[EvidenceItem]:
        # 1. Validate the upload before trusting any of its bytes.
        validation = validate_file(file_content, mime_type or "application/octet-stream")
        if not validation.valid:
            raise ValueError(f"File rejected: {'; '.join(validation.issues)}")

        # 2. Screen for prompt injection. Evidence is DATA, not instructions, so
        #    we do not abort — we flag it, and analysis routes such cases to a
        #    human via the gate. We never log the raw content (it may hold PII).
        content_str = file_content.decode(errors="ignore")
        injection = detect_injection(content_str)
        if injection.detected:
            logger.warning(
                "injection_detected_on_upload",
                case_id=case_id,
                file_path=file_path,
                patterns=injection.patterns_matched,
            )

        # 3. Deterministic ingestion (parse + regex facts + classification).
        evidence_items = ingest_evidence_file(file_path, file_content, mime_type or "", case_id)

        # 4. Optional LLM extraction proposes additional facts; each is stamped
        #    with the item's content hash so it can only survive grounding if it
        #    genuinely appears in the source content.
        results: List[EvidenceItem] = []
        for item in evidence_items:
            if item.raw_content:
                try:
                    extraction = await self.extractor.extract(item.raw_content, item.source_type)
                    facts = self.extractor.to_extracted_facts(extraction, item.id, item.raw_content)
                    item.extracted_facts.extend(facts)
                except Exception as exc:  # extraction is best-effort; never fail ingestion on it
                    logger.warning("llm_extraction_failed", case_id=case_id, evidence_id=item.id, error=str(exc))
            await self.evidence_repo.create_evidence(item)
            results.append(item)

        await self._audit(
            case_id, "INGESTION", f"EVIDENCE_ADDED:{len(results)}", 1.0, model=self.llm_model_name
        )
        return results

    async def analyze_case(self, case_id: str) -> CaseAnalysisResult:
        case = await self.case_repo.get_case(case_id)
        if case is None:
            raise ValueError(f"Case {case_id} not found")
        evidence_items = await self.evidence_repo.get_evidence_by_case(case_id)

        # The entire decision is the pure core; the service only does I/O.
        analysis = analyze_evidence(case, evidence_items)

        # --- Persist analysis idempotently ------------------------------------
        await self.claim_repo.delete_claims_by_case(case_id)
        for claim in analysis.claims:
            await self.claim_repo.create_claim(claim, case_id)

        await self.timeline_repo.delete_timeline_by_case(case_id)
        for event in analysis.timeline:
            await self.timeline_repo.create_event(event, case_id)

        case.status = (
            CaseStatus.PACKAGE_READY
            if analysis.gate_result.gate_status == GateStatus.READY
            else CaseStatus.REVIEW_REQUIRED
        )
        case.updated_at = now_utc()
        await self.case_repo.update_case(case)

        await self._audit(
            case_id, "VERIFICATION", analysis.gate_result.gate_status.value, analysis.score.total_score / 100.0
        )
        return analysis

    async def generate_package(self, case_id: str) -> EvidencePackage:
        analysis = await self.analyze_case(case_id)

        from src.packaging.builder import build_evidence_package

        package = build_evidence_package(analysis.case, analysis)

        analysis.case.package = package
        analysis.case.updated_at = now_utc()
        await self.case_repo.update_case(analysis.case)

        await self._audit(case_id, "PACKAGING", "PACKAGE_GENERATED_DRAFT", 1.0, model=self.llm_model_name)
        return package
