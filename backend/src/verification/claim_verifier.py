"""Claim grounding via cryptographic provenance.

This is where "NEVER INVENT EVIDENCE" is enforced mechanically. A claim is an
assertion the system intends to make in the merchant's defense; it may only be
``VERIFIED`` if it is *grounded* — i.e. backed by at least one extracted fact
that passes two checks against its cited source evidence:

1. **Integrity** — the fact's recorded ``provenance.content_hash`` equals the
   SHA-256 of the evidence's current ``raw_content``. If the content changed
   after extraction (or the hash was fabricated), integrity fails.
2. **Grounding** — the fact's value actually appears in that raw content, so we
   are not asserting something merely attributed to the source.

A claim citing missing evidence is ``BLOCKED``. A claim whose supporting facts
cannot be grounded is ``BLOCKED`` with a reason. Only genuinely traceable
claims survive into the evidence package — everything else is withheld rather
than guessed.
"""

from typing import List

from src.domain.enums import ClaimStatus
from src.domain.models import Claim, EvidenceItem, Provenance


def _grounds_claim(evidence: EvidenceItem) -> bool:
    """True if at least one fact on ``evidence`` passes integrity + grounding."""
    if not evidence.raw_content:
        return False
    content_hash = Provenance.compute_hash(evidence.raw_content)
    lowered = evidence.raw_content.lower()
    for fact in evidence.extracted_facts:
        integrity_ok = fact.provenance.content_hash == content_hash
        grounded = fact.value.strip().lower() in lowered
        if integrity_ok and grounded:
            return True
    return False


def verify_claim(claim: Claim, evidence_items: List[EvidenceItem]) -> Claim:
    """Verify a claim against its supporting evidence using provenance hashes.

    Args:
        claim: The claim to verify (its ``supporting_evidence_ids`` are checked).
        evidence_items: All evidence available for the case.

    Returns:
        The same claim with ``status`` set to ``VERIFIED`` or ``BLOCKED`` (and a
        ``block_reason`` when blocked).
    """
    evidence_by_id = {e.id: e for e in evidence_items}

    if not claim.supporting_evidence_ids:
        claim.status = ClaimStatus.BLOCKED
        claim.block_reason = "Claim cites no supporting evidence."
        return claim

    grounded_any = False
    for ev_id in claim.supporting_evidence_ids:
        evidence = evidence_by_id.get(ev_id)
        if evidence is None:
            claim.status = ClaimStatus.BLOCKED
            claim.block_reason = f"Supporting evidence {ev_id} not found."
            return claim
        if _grounds_claim(evidence):
            grounded_any = True

    if grounded_any:
        claim.status = ClaimStatus.VERIFIED
        claim.block_reason = None
    else:
        claim.status = ClaimStatus.BLOCKED
        claim.block_reason = (
            "No supporting fact could be cryptographically grounded to its source content "
            "(hash integrity or value grounding failed)."
        )
    return claim
