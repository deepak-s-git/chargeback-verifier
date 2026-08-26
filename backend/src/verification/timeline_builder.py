from datetime import datetime, timezone
from src.domain.models import EvidenceItem, TimelineEvent, TimelineAnomaly
from src.domain.enums import FactType, TimelineAnomalyType

def build_timeline(evidence_items: list[EvidenceItem]) -> list[TimelineEvent]:
    events = []
    for evidence in evidence_items:
        for fact in evidence.extracted_facts:
            if fact.type == FactType.TIMESTAMP:
                try:
                    dt = datetime.fromisoformat(fact.value)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    events.append(TimelineEvent(
                        timestamp=dt,
                        description=f"Event from {evidence.id}",
                        evidence_id=evidence.id
                    ))
                except ValueError:
                    continue
                    
    events.sort(key=lambda x: x.timestamp)
    
    # Anomaly detection
    now = datetime.now(timezone.utc)
    for i, event in enumerate(events):
        if event.timestamp > now:
            event.anomalies.append(TimelineAnomaly(
                type=TimelineAnomalyType.FUTURE_TIMESTAMP,
                description="Timestamp is in the future",
                severity="HIGH"
            ))
            
        if i > 0:
            prev_event = events[i-1]
            if event.timestamp == prev_event.timestamp:
                event.anomalies.append(TimelineAnomaly(
                    type=TimelineAnomalyType.DUPLICATE_EVENT,
                    description="Duplicate timestamp",
                    severity="LOW"
                ))
    
    return events
