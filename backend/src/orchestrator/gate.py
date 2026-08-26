from enum import Enum
from typing import List

from pydantic import BaseModel

from src.domain.models import EvidenceScore, Contradiction, Claim
from src.domain.enums import Recommendation, ClaimStatus

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

def apply_gate(score: EvidenceScore, contradictions: List[Contradiction], claims: List[Claim]) -> GateResult:
    """Apply gating logic for human review based on contradictions, claims, and score."""
    reasons = []
    blocked_claims = [c for c in claims if getattr(c, "status", None) == ClaimStatus.BLOCKED]
    
    if contradictions:
        reasons.append(f"Found {len(contradictions)} contradictions.")
    if blocked_claims:
        reasons.append(f"Found {len(blocked_claims)} blocked claims.")
        
    if contradictions or blocked_claims:
        return GateResult(
            gate_status=GateStatus.MANDATORY_REVIEW,
            reasons=reasons,
            blocked_claims=blocked_claims,
            contradictions=contradictions
        )
        
    if score.recommendation == Recommendation.CONTEST:
        return GateResult(
            gate_status=GateStatus.READY,
            reasons=["High confidence score, ready for submission."],
            blocked_claims=[],
            contradictions=[]
        )
        
    if score.recommendation == Recommendation.REVIEW:
        return GateResult(
            gate_status=GateStatus.NEEDS_REVIEW,
            reasons=["Score requires human review."],
            blocked_claims=[],
            contradictions=[]
        )
        
    return GateResult(
        gate_status=GateStatus.NOT_RECOMMENDED,
        reasons=["Case is not recommended for contest."],
        blocked_claims=[],
        contradictions=[]
    )
