from pydantic import BaseModel

class CaseGroundTruth(BaseModel):
    case_id: str
    expected_recommendation: str  # contest, review, insufficient, abstain
    expected_score_range: tuple[int, int]  # e.g. (75, 95)
    requirement_labels: dict[str, str]  # req_name -> satisfied/partial/missing/contradicted
    expected_contradictions: int  # count of contradictions
    has_injection: bool
    failure_type: str | None  # insufficient_evidence, contradictory, noisy, adversarial
    notes: str
