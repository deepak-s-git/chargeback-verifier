from src.domain.models import EvidenceItem, TimelineEvent, Contradiction

def detect_contradictions(evidence_items: list[EvidenceItem], timeline: list[TimelineEvent]) -> list[Contradiction]:
    contradictions = []
    # 1. Timestamp contradictions
    for i, event1 in enumerate(timeline):
        for event2 in timeline[i+1:]:
            if event1.timestamp > event2.timestamp:
                contradictions.append(Contradiction(
                    evidence_a_id=event1.evidence_id,
                    evidence_b_id=event2.evidence_id,
                    description=f"Event {event1.id} happens before {event2.id} but timestamps are reversed.",
                    severity="HIGH",
                    type="TIMESTAMP_CONTRADICTION"
                ))
    
    # Add other contradiction types as required
    return contradictions
