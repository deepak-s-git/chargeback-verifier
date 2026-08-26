from src.domain.models import Claim, EvidenceItem
from src.domain.enums import ClaimStatus

def verify_claim(claim: Claim, evidence_items: list[EvidenceItem]) -> Claim:
    evidence_dict = {e.id: e for e in evidence_items}
    for ev_id in claim.supporting_evidence_ids:
        if ev_id not in evidence_dict:
            claim.status = ClaimStatus.BLOCKED
            claim.block_reason = f"Supporting evidence {ev_id} not found."
            return claim
            
        evidence = evidence_dict[ev_id]
        if evidence.raw_content and claim.description.lower() not in evidence.raw_content.lower():
            # For simplicity in keyword matching
            claim.status = ClaimStatus.NEEDS_REVIEW
            return claim
            
    claim.status = ClaimStatus.VERIFIED
    return claim
