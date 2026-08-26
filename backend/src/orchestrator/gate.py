"""Human-review gating.

The gate is the last deterministic checkpoint before a package is considered
"ready". It is deliberately conservative and *defense-first*: any signal that a
human must look — a detected contradiction, a blocked (ungroundable) claim, or
prompt injection in the evidence — forces ``MANDATORY_REVIEW`` regardless of the
numeric score. Only a clean case whose recommendation is ``CONTEST`` is marked
``READY`` (which still means "ready for a human to submit", never auto-submit).
"""

from enum import Enum
from typing import List

from pydantic import BaseModel

from src.domain.enums import ClaimStatus, Recommendation
from src.domain.models import Claim, Contradiction, EvidenceScore


class GateStatus(str, Enum):
    MANDATORY_REVIEW = "MANDATORY_REVIEW"
    READY = "READY"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    NOT_RECOMMENDED = "NOT_RECOMMENDED"


class GateResult(BaseModel):
    gate_status: GateStatus
    reasons: List[str]
    blocked_claims: List[Claim]
    contradictions: List[Contradiction]


def apply_gate(
    score: EvidenceScore,
    contradictions: List[Contradiction],
    claims: List[Claim],
    injection_detected: bool = False,
) -> GateResult:
    """Decide whether a case is ready, needs review, or is not recommended.

    Args:
        score: The computed evidence score and recommendation.
        contradictions: Contradictions detected in the evidence.
        claims: The (already verified) claims for the case.
        injection_detected: Whether prompt injection was found in any evidence.

    Returns:
        A :class:`GateResult` with a status and human-readable reasons.
    """
    reasons: List[str] = []
    blocked_claims = [c for c in claims if getattr(c, "status", None) == ClaimStatus.BLOCKED]

    if contradictions:
        reasons.append(f"Found {len(contradictions)} contradiction(s) that a human must adjudicate.")
    if blocked_claims:
        reasons.append(f"{len(blocked_claims)} claim(s) could not be grounded in evidence and were blocked.")
    if injection_detected:
        reasons.append("Prompt-injection content detected in evidence; treated as untrusted and routed to a human.")

    if contradictions or blocked_claims or injection_detected:
        return GateResult(
            gate_status=GateStatus.MANDATORY_REVIEW,
            reasons=reasons,
            blocked_claims=blocked_claims,
            contradictions=contradictions,
        )

    if score.recommendation == Recommendation.CONTEST:
        return GateResult(
            gate_status=GateStatus.READY,
            reasons=["Evidence supports a contest; ready for human sign-off before submission."],
            blocked_claims=[],
            contradictions=[],
        )

    if score.recommendation == Recommendation.REVIEW:
        return GateResult(
            gate_status=GateStatus.NEEDS_REVIEW,
            reasons=["Evidence is mixed; a human should review before deciding."],
            blocked_claims=[],
            contradictions=[],
        )

    return GateResult(
        gate_status=GateStatus.NOT_RECOMMENDED,
        reasons=["Evidence is insufficient to support a contest."],
        blocked_claims=[],
        contradictions=[],
    )
