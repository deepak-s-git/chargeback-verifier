"""Compile the final, bounded evidence package.

The builder assembles the analysis outputs into an :class:`EvidencePackage`,
records the recommendation and the human-review verdict from the gate, and
attaches an inert Razorpay *draft* (``action='draft'``). It never invents
narrative: the package carries exactly the claims, requirements, timeline and
contradictions that analysis produced, and the network submission is derived
solely from verified claims.

Fixes over the previous version: it referenced ``case.card_network`` (the field
is ``network``) and used the deprecated naive ``datetime.utcnow()``.
"""

from typing import TYPE_CHECKING

from src.domain.models import DisputeCase, EvidencePackage, now_utc
from src.orchestrator.gate import GateStatus
from src.packaging.razorpay_mapper import map_to_razorpay
from src.packaging.templates import get_template

if TYPE_CHECKING:
    from src.orchestrator.analysis import CaseAnalysisResult


def build_evidence_package(case: DisputeCase, analysis: "CaseAnalysisResult") -> EvidencePackage:
    """Build the compiled defense package for a case.

    Args:
        case: The dispute case.
        analysis: The completed analysis (requirements, claims, timeline, etc.).

    Returns:
        A fully-populated :class:`EvidencePackage` including an inert network draft.
    """
    # Template selection (kept for section ordering / future rendering); driven
    # by the correct ``network`` field.
    _ = get_template(case.network, case.reason_code)

    review_required = analysis.gate_result.gate_status != GateStatus.READY

    package = EvidencePackage(
        case_id=case.id,
        claims=analysis.claims,
        requirements=analysis.requirements,
        score=analysis.score,
        timeline=analysis.timeline,
        contradictions=analysis.contradictions,
        recommendation=analysis.score.recommendation,
        review_required=review_required,
        review_reasons=analysis.gate_result.reasons,
        generated_at=now_utc(),
    )

    # Attach the inert draft last, once the package it derives from is complete.
    package.network_submission = map_to_razorpay(package)
    return package
