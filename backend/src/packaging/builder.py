from datetime import datetime
from src.domain.models import DisputeCase, EvidencePackage
from src.orchestrator.case_service import CaseAnalysisResult
from src.packaging.templates import get_template

def build_evidence_package(case: DisputeCase, analysis: CaseAnalysisResult) -> EvidencePackage:
    """Builds the final evidence package with provenance links and rebuttal."""
    template = get_template(case.card_network, case.reason_code)
    
    # In a real system, we would generate a rebuttal text using the LLM here,
    # ensuring all claims include [EV-xxx] style provenance links.
    
    return EvidencePackage(
        case_id=case.id,
        claims=analysis.claims,
        requirements=analysis.requirements,
        score=analysis.score,
        timeline=analysis.timeline,
        contradictions=analysis.contradictions,
        generated_at=datetime.utcnow()
    )
