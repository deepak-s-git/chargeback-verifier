"""Visa Compelling Evidence 3.0 (CE 3.0) qualification engine.

Visa CE 3.0 lets a merchant obtain a liability shift on a 10.4 (fraud) dispute
by showing a history of legitimate use. The bar is specific:

* **At least two** prior **undisputed** transactions,
* each dated **120–365 days before** the disputed transaction,
* each sharing **two or more matching data elements** with the disputed
  transaction, where **at least one** matching element is an **IP address** or
  **Device ID/fingerprint**.

The previous implementation had two defects this rewrite corrects:

1. It required only *one* matching element (``len(matches) > 0``) instead of
   two, so weak histories qualified.
2. It measured the window from ``created_at`` (when the *case* was opened)
   rather than the disputed transaction date. We now use
   :pyattr:`DisputeCase.effective_transaction_date`.
"""

from datetime import timezone
from typing import Dict, List, Set

from pydantic import BaseModel, Field

from src.domain.enums import EvidenceType, FactType
from src.domain.models import DisputeCase, EvidenceItem
from src.ingestion.normalizer import normalize_timestamp

# Data elements Visa recognises for CE 3.0 matching.
_MATCHABLE_ELEMENTS: Dict[FactType, str] = {
    FactType.IP_ADDRESS: "IP",
    FactType.DEVICE_ID: "DeviceID",
    FactType.DEVICE_FINGERPRINT: "DeviceFingerprint",
    FactType.ACCOUNT_ID: "AccountID",
    FactType.EMAIL_ADDRESS: "Email",
}

# At least one matching element must come from this anchor set.
_ANCHOR_ELEMENTS: Set[str] = {"IP", "DeviceID", "DeviceFingerprint"}

CE30_MIN_DAYS = 120
CE30_MAX_DAYS = 365
CE30_MIN_MATCHING_ELEMENTS = 2
CE30_MIN_QUALIFYING_TXNS = 2


class QualifyingTransaction(BaseModel):
    """A single historical transaction that meets the CE 3.0 bar."""

    evidence_id: str
    days_before_dispute: int
    matching_elements: List[str]


class CE30Result(BaseModel):
    qualified: bool
    matching_elements: List[str] = Field(default_factory=list)
    qualifying_transactions: List[str] = Field(default_factory=list)
    qualifying_details: List[QualifyingTransaction] = Field(default_factory=list)
    reason: str


def _element_values(item: EvidenceItem) -> Dict[str, Set[str]]:
    """Collect matchable data-element values from an evidence item."""
    out: Dict[str, Set[str]] = {}
    for fact in item.extracted_facts:
        label = _MATCHABLE_ELEMENTS.get(fact.type)
        if label is None:
            continue
        out.setdefault(label, set()).add(fact.value.strip().lower())
    return out


def evaluate_ce30(disputed_txn: DisputeCase, evidence_items: List[EvidenceItem]) -> CE30Result:
    """Evaluate Visa CE 3.0 qualification for a dispute.

    Args:
        disputed_txn: The dispute case (provides the transaction date).
        evidence_items: All evidence for the case, including historical matches.

    Returns:
        A :class:`CE30Result` describing whether the case qualifies and why.
    """
    historical_items = [e for e in evidence_items if e.semantic_type == EvidenceType.HISTORICAL_MATCH]
    if not historical_items:
        return CE30Result(qualified=False, reason="No historical transactions provided.")

    # Data elements of the *disputed* transaction, pooled from its (non-historical) evidence.
    disputed: Dict[str, Set[str]] = {}
    for e in evidence_items:
        if e.semantic_type == EvidenceType.HISTORICAL_MATCH:
            continue
        for label, values in _element_values(e).items():
            disputed.setdefault(label, set()).update(values)

    if not disputed:
        return CE30Result(
            qualified=False,
            reason="No identifying data elements found on the disputed transaction to match against.",
        )

    dispute_date = disputed_txn.effective_transaction_date
    if dispute_date.tzinfo is None:
        dispute_date = dispute_date.replace(tzinfo=timezone.utc)

    qualifying: List[QualifyingTransaction] = []
    all_matching: Set[str] = set()

    for hist in historical_items:
        # Historical transaction date.
        hist_date = None
        for fact in hist.extracted_facts:
            if fact.type == FactType.TIMESTAMP:
                hist_date = normalize_timestamp(fact.value)
                if hist_date:
                    break
        if hist_date is None:
            continue
        if hist_date.tzinfo is None:
            hist_date = hist_date.replace(tzinfo=timezone.utc)

        days_diff = (dispute_date - hist_date).days
        if not (CE30_MIN_DAYS <= days_diff <= CE30_MAX_DAYS):
            continue

        # Matching data elements (value-level intersection).
        hist_elements = _element_values(hist)
        matches = [
            label
            for label, values in hist_elements.items()
            if label in disputed and values & disputed[label]
        ]

        has_anchor = bool(set(matches) & _ANCHOR_ELEMENTS)
        if len(matches) >= CE30_MIN_MATCHING_ELEMENTS and has_anchor:
            qualifying.append(
                QualifyingTransaction(
                    evidence_id=hist.id,
                    days_before_dispute=days_diff,
                    matching_elements=sorted(matches),
                )
            )
            all_matching.update(matches)

    if len(qualifying) >= CE30_MIN_QUALIFYING_TXNS:
        return CE30Result(
            qualified=True,
            matching_elements=sorted(all_matching),
            qualifying_transactions=[q.evidence_id for q in qualifying],
            qualifying_details=qualifying,
            reason=(
                f"Found {len(qualifying)} prior undisputed transactions 120-365 days before the "
                f"disputed transaction, each sharing ≥2 data elements including an IP/Device anchor."
            ),
        )

    return CE30Result(
        qualified=False,
        matching_elements=sorted(all_matching),
        qualifying_transactions=[q.evidence_id for q in qualifying],
        qualifying_details=qualifying,
        reason=(
            f"Only {len(qualifying)} qualifying historical transaction(s) found; CE 3.0 requires "
            f"{CE30_MIN_QUALIFYING_TXNS} with ≥2 matching elements (one being IP/Device)."
        ),
    )
