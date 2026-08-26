"""Deterministic contradiction detection.

Contradictions are the strongest possible signal that a case must go to a human
rather than be contested automatically — evidence that disagrees with itself, or
with the cardholder's own statements, cannot support an honest defense. This
module replaces the previous no-op (which compared a pre-sorted timeline against
itself and could never fire) with five real, independent detectors:

1. **IP mismatch** — the IP that accessed the product does not match the IP
   associated with the cardholder's identity/payment.
2. **Identity mismatch** — multiple distinct customer emails across evidence.
3. **Amount mismatch** — an extracted amount materially disagrees with the
   disputed transaction amount.
4. **Timeline order** — product access/delivery predates the transaction, or a
   timestamp lies in the future. (Authentication legitimately precedes a
   purchase, so it is not treated as an ordering contradiction.)
5. **Customer-statement conflict** — the cardholder says they never
   received/authorised the purchase, yet access/delivery/auth evidence exists.

Every detector is deterministic and traceable to specific evidence ids.
"""

from typing import Dict, List, Optional, Set

from src.domain.enums import ContradictionType, EvidenceType, FactType, TimelineAnomalyType
from src.domain.models import Contradiction, DisputeCase, EvidenceItem, TimelineEvent
from src.ingestion.normalizer import normalize_amount

# Phrases in customer communication that assert non-use / non-authorisation.
_DENIAL_PHRASES = (
    "never received",
    "did not receive",
    "never got",
    "did not authorize",
    "did not authorise",
    "didn't authorize",
    "never authorized",
    "unauthorized",
    "unauthorised",
    "never bought",
    "did not buy",
    "didn't order",
    "did not order",
    "never ordered",
    "did not make this purchase",
    "i never purchased",
)

_ACCESS_LIKE = {EvidenceType.ACCESS_PROOF, EvidenceType.DELIVERY_PROOF, EvidenceType.AUTHENTICATION_PROOF}
_IDENTITY_LIKE = {EvidenceType.IDENTITY_PROOF, EvidenceType.PAYMENT_PROOF, EvidenceType.AUTHENTICATION_PROOF}

# An extracted amount within this fraction of the disputed amount is "the same".
_AMOUNT_TOLERANCE = 0.01


def _values_of(item: EvidenceItem, fact_type: FactType) -> Set[str]:
    return {f.value.strip().lower() for f in item.extracted_facts if f.type == fact_type}


def _detect_ip_mismatch(evidence_items: List[EvidenceItem]) -> List[Contradiction]:
    access_ips: Dict[str, str] = {}   # ip -> evidence_id (first seen)
    identity_ips: Dict[str, str] = {}

    for e in evidence_items:
        ips = _values_of(e, FactType.IP_ADDRESS)
        if not ips:
            continue
        if e.semantic_type in _ACCESS_LIKE:
            for ip in ips:
                access_ips.setdefault(ip, e.id)
        if e.semantic_type in _IDENTITY_LIKE:
            for ip in ips:
                identity_ips.setdefault(ip, e.id)

    if not access_ips or not identity_ips:
        return []
    if set(access_ips) & set(identity_ips):
        return []  # they share at least one IP — consistent

    access_ip, access_ev = next(iter(access_ips.items()))
    identity_ip, identity_ev = next(iter(identity_ips.items()))
    return [
        Contradiction(
            evidence_a_id=access_ev,
            evidence_b_id=identity_ev,
            description=(
                f"Access originated from IP {access_ip}, which does not match the "
                f"identity/payment IP {identity_ip} on file."
            ),
            severity="HIGH",
            type=ContradictionType.IP_MISMATCH.value,
        )
    ]


def _detect_identity_mismatch(evidence_items: List[EvidenceItem]) -> List[Contradiction]:
    email_to_ev: Dict[str, str] = {}
    for e in evidence_items:
        for email in _values_of(e, FactType.EMAIL_ADDRESS):
            email_to_ev.setdefault(email, e.id)
    if len(email_to_ev) < 2:
        return []
    (email_a, ev_a), (email_b, ev_b) = list(email_to_ev.items())[:2]
    return [
        Contradiction(
            evidence_a_id=ev_a,
            evidence_b_id=ev_b,
            description=f"Conflicting customer emails across evidence: {email_a} vs {email_b}.",
            severity="MEDIUM",
            type=ContradictionType.IDENTITY_MISMATCH.value,
        )
    ]


def _detect_amount_mismatch(evidence_items: List[EvidenceItem], case: Optional[DisputeCase]) -> List[Contradiction]:
    if case is None:
        return []
    expected = normalize_amount(str(case.amount), case.currency)
    if expected is None:
        return []
    for e in evidence_items:
        if e.semantic_type != EvidenceType.PAYMENT_PROOF:
            continue
        for raw in _values_of(e, FactType.AMOUNT):
            got = normalize_amount(raw, case.currency)
            if got is None:
                continue
            if expected == 0:
                continue
            if abs(got - expected) / expected > _AMOUNT_TOLERANCE:
                return [
                    Contradiction(
                        evidence_a_id=e.id,
                        description=(
                            f"Payment evidence shows amount {got / 100:.2f} but the disputed "
                            f"transaction is {expected / 100:.2f} {case.currency}."
                        ),
                        severity="HIGH",
                        type=ContradictionType.AMOUNT_MISMATCH.value,
                    )
                ]
    return []


def _detect_timeline_order(
    evidence_items: List[EvidenceItem],
    timeline: List[TimelineEvent],
    case: Optional[DisputeCase],
) -> List[Contradiction]:
    contradictions: List[Contradiction] = []

    # Future timestamps promoted from timeline anomalies.
    for event in timeline:
        if any(a.type == TimelineAnomalyType.FUTURE_TIMESTAMP for a in event.anomalies):
            contradictions.append(
                Contradiction(
                    evidence_a_id=event.evidence_id,
                    description=f"Evidence timestamp {event.timestamp.isoformat()} is in the future.",
                    severity="MEDIUM",
                    type=ContradictionType.FUTURE_TIMESTAMP.value,
                )
            )

    # Usage/access before the transaction occurred. Only product ACCESS or
    # DELIVERY counts: authentication (AUTH) normally happens just before a
    # purchase, so an auth timestamp preceding the transaction is expected, not
    # contradictory. Including it here would false-positive on every 3-D Secure
    # / MFA flow.
    if case is not None:
        tx_time = case.effective_transaction_date
        access_events = [
            ev for ev in timeline
            if ev.event_type in {"ACCESS", "DELIVERY"} and ev.timestamp < tx_time
        ]
        for ev in access_events[:1]:
            contradictions.append(
                Contradiction(
                    evidence_a_id=ev.evidence_id,
                    description=(
                        f"Product access at {ev.timestamp.isoformat()} predates the disputed "
                        f"transaction at {tx_time.isoformat()}."
                    ),
                    severity="HIGH",
                    type=ContradictionType.USAGE_BEFORE_PURCHASE.value,
                )
            )
    return contradictions


def _detect_customer_statement_conflict(evidence_items: List[EvidenceItem]) -> List[Contradiction]:
    has_usage_evidence = any(e.semantic_type in _ACCESS_LIKE for e in evidence_items)
    if not has_usage_evidence:
        return []

    usage_ev = next(e.id for e in evidence_items if e.semantic_type in _ACCESS_LIKE)
    for e in evidence_items:
        if e.semantic_type != EvidenceType.COMMUNICATION or not e.raw_content:
            continue
        lowered = e.raw_content.lower()
        for phrase in _DENIAL_PHRASES:
            if phrase in lowered:
                return [
                    Contradiction(
                        evidence_a_id=e.id,
                        evidence_b_id=usage_ev,
                        description=(
                            f"Cardholder statement (\"{phrase}\") conflicts with access/delivery "
                            f"evidence showing the product was used."
                        ),
                        severity="HIGH",
                        type=ContradictionType.CUSTOMER_STATEMENT_CONFLICT.value,
                    )
                ]
    return []


def detect_contradictions(
    evidence_items: List[EvidenceItem],
    timeline: List[TimelineEvent],
    case: Optional[DisputeCase] = None,
) -> List[Contradiction]:
    """Run all contradiction detectors and return the union of findings.

    Args:
        evidence_items: The evidence gathered for the case.
        timeline: The reconstructed, enriched timeline.
        case: The dispute case, used for amount/transaction-time checks.

    Returns:
        A list of :class:`Contradiction` objects, most-severe categories first.
    """
    contradictions: List[Contradiction] = []
    contradictions += _detect_ip_mismatch(evidence_items)
    contradictions += _detect_customer_statement_conflict(evidence_items)
    contradictions += _detect_amount_mismatch(evidence_items, case)
    contradictions += _detect_timeline_order(evidence_items, timeline, case)
    contradictions += _detect_identity_mismatch(evidence_items)
    return contradictions
