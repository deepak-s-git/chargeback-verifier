"""Map a compiled evidence package to a Razorpay dispute-contest draft.

This is the *only* boundary that speaks the payment network's language, and it
is deliberately inert: ``action`` is hard-coded to ``"draft"`` and there is no
code path that sets it to ``"submit"``. DisputeShield compiles a defense; a
human submits it. The draft is assembled strictly from **verified** claims and
their cited evidence — nothing unsupported leaks into the payload.
"""

from typing import Any, Dict, List

from src.domain.enums import ClaimStatus
from src.domain.models import EvidencePackage

# Timeline event types that constitute access/service activity vs communication.
_ACTIVITY_EVENTS = {"ACCESS", "DELIVERY", "AUTH", "PAYMENT", "HISTORICAL"}
_COMMUNICATION_EVENTS = {"COMMUNICATION"}


def _explanation_letter(package: EvidencePackage) -> str:
    """A citation-bearing narrative built only from verified claims."""
    verified = [c for c in package.claims if c.status == ClaimStatus.VERIFIED]
    if not verified:
        return (
            "No claim could be cryptographically grounded in the submitted evidence. "
            "This dispute is not supported for contest and requires manual review."
        )
    lines = [
        "This response is compiled from verified evidence only. Each assertion cites "
        "the evidence item(s) that ground it.",
        "",
    ]
    for claim in verified:
        citations = ", ".join(f"[{ev_id}]" for ev_id in claim.supporting_evidence_ids)
        lines.append(f"- {claim.description} {citations}".rstrip())
    return "\n".join(lines)


def map_to_razorpay(package: EvidencePackage) -> Dict[str, Any]:
    """Map an :class:`EvidencePackage` to a Razorpay contest **draft** payload.

    Args:
        package: The compiled evidence package.

    Returns:
        A dict shaped like Razorpay's dispute-contest evidence schema, with
        ``action='draft'`` (never ``'submit'``).
    """
    verified = [c for c in package.claims if c.status == ClaimStatus.VERIFIED]

    activity_evidence: List[str] = []
    communication_evidence: List[str] = []
    for event in package.timeline:
        if event.event_type in _ACTIVITY_EVENTS and event.evidence_id not in activity_evidence:
            activity_evidence.append(event.evidence_id)
        elif event.event_type in _COMMUNICATION_EVENTS and event.evidence_id not in communication_evidence:
            communication_evidence.append(event.evidence_id)

    return {
        "action": "draft",  # INVARIANT: DisputeShield never submits automatically.
        "summary": (
            f"{len(verified)} verified claim(s); "
            f"{len(package.contradictions)} contradiction(s); "
            f"recommendation={package.recommendation.value if package.recommendation else 'UNKNOWN'}."
        ),
        "review_required": package.review_required,
        "review_reasons": package.review_reasons,
        "explanation_letter": _explanation_letter(package),
        "access_activity_log": activity_evidence,
        "customer_communication": communication_evidence,
        "billing_proof": [c.supporting_evidence_ids for c in verified],
        "supported_claims": [
            {"claim": c.description, "evidence": c.supporting_evidence_ids} for c in verified
        ],
    }
