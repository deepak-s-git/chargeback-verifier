"""Timeline reconstruction from timestamped facts.

Builds a chronologically ordered list of :class:`TimelineEvent` from the
``TIMESTAMP`` facts across all evidence, enriching each event with a semantic
type, the acting party, and an originating IP where those are derivable from the
same evidence item. Timestamps are parsed through the shared
:func:`normalize_timestamp` (dateparser-backed) rather than a bare
``fromisoformat`` so heterogeneous formats survive ingestion.

Two per-event anomalies are flagged here: timestamps in the future and exact
duplicates. Cross-event ordering problems (e.g. access before purchase) are the
contradiction detector's job, which consumes this enriched timeline.
"""

from datetime import datetime, timezone
from typing import List, Optional

from src.domain.enums import EvidenceType, FactType, TimelineAnomalyType
from src.domain.models import EvidenceItem, TimelineAnomaly, TimelineEvent
from src.ingestion.normalizer import normalize_timestamp

# Map evidence semantic type to a coarse timeline event type.
_EVENT_TYPE_BY_SEMANTIC = {
    EvidenceType.PAYMENT_PROOF: "PAYMENT",
    EvidenceType.ACCESS_PROOF: "ACCESS",
    EvidenceType.DELIVERY_PROOF: "DELIVERY",
    EvidenceType.AUTHENTICATION_PROOF: "AUTH",
    EvidenceType.COMMUNICATION: "COMMUNICATION",
    EvidenceType.IDENTITY_PROOF: "IDENTITY",
    EvidenceType.HISTORICAL_MATCH: "HISTORICAL",
    EvidenceType.POLICY_DOCUMENT: "CONSENT",
    EvidenceType.USAGE_METRICS: "USAGE",
}


def _first_value(evidence: EvidenceItem, *fact_types: FactType) -> Optional[str]:
    for fact_type in fact_types:
        for fact in evidence.extracted_facts:
            if fact.type == fact_type:
                return fact.value
    return None


def _describe(event_type: str, actor: Optional[str], ip: Optional[str]) -> str:
    label = event_type.replace("_", " ").title()
    parts = [f"{label} event"]
    if actor:
        parts.append(f"by {actor}")
    if ip:
        parts.append(f"from {ip}")
    return " ".join(parts)


def build_timeline(evidence_items: List[EvidenceItem]) -> List[TimelineEvent]:
    """Reconstruct an ordered, enriched timeline from evidence timestamps.

    Args:
        evidence_items: The evidence gathered for the case.

    Returns:
        Timeline events sorted ascending by timestamp, each annotated with a
        semantic type, actor, IP, and any per-event anomalies.
    """
    events: List[TimelineEvent] = []

    for evidence in evidence_items:
        event_type = _EVENT_TYPE_BY_SEMANTIC.get(evidence.semantic_type, "EVENT")
        actor = _first_value(evidence, FactType.ACCOUNT_ID, FactType.CUSTOMER_NAME, FactType.EMAIL_ADDRESS)
        ip = _first_value(evidence, FactType.IP_ADDRESS)

        for fact in evidence.extracted_facts:
            if fact.type != FactType.TIMESTAMP:
                continue
            dt = normalize_timestamp(fact.value)
            if dt is None:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            events.append(
                TimelineEvent(
                    timestamp=dt,
                    description=_describe(event_type, actor, ip),
                    evidence_id=evidence.id,
                    event_type=event_type,
                    actor=actor,
                    ip_address=ip,
                )
            )

    events.sort(key=lambda e: e.timestamp)

    now = datetime.now(timezone.utc)
    for i, event in enumerate(events):
        if event.timestamp > now:
            event.anomalies.append(
                TimelineAnomaly(
                    type=TimelineAnomalyType.FUTURE_TIMESTAMP,
                    description="Timestamp is in the future relative to analysis time.",
                    severity="HIGH",
                )
            )
        if i > 0:
            prev = events[i - 1]
            if event.timestamp == prev.timestamp and event.event_type == prev.event_type:
                event.anomalies.append(
                    TimelineAnomaly(
                        type=TimelineAnomalyType.DUPLICATE_EVENT,
                        description="Duplicate timestamp for the same event type.",
                        severity="LOW",
                    )
                )

    return events
