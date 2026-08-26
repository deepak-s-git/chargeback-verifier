import pytest
from datetime import datetime, timezone, timedelta
from src.domain.enums import FactType, EvidenceType, RequirementStatus, CardNetwork, Recommendation
from src.domain.models import DisputeCase, EvidenceItem, ExtractedFact, Requirement, Contradiction, Provenance
from src.domain.rules import get_requirements
from src.verification.requirement_engine import evaluate_requirements
from src.verification.ce30_matcher import evaluate_ce30
from src.scoring.scorer import score_evidence

def test_requirement_evaluation():
    reqs = get_requirements(CardNetwork.VISA, "10.4")
    assert len(reqs) > 0
    
    case = DisputeCase(merchant_id="m1", transaction_id="t1", amount=100.0, currency="USD", network=CardNetwork.VISA, reason_code="10.4")
    prov = Provenance(source_file="test", source_location="1", content_hash="hash")
    
    # Evidence satisfying Payment Verification
    ev = EvidenceItem(
        case_id=case.id,
        source_type="OTHER",
        semantic_type=EvidenceType.PAYMENT_PROOF,
        extracted_facts=[
            ExtractedFact(type=FactType.PAYMENT_ID, value="p1", confidence=1.0, extraction_method="REGEX", provenance=prov),
            ExtractedFact(type=FactType.AMOUNT, value="100", confidence=1.0, extraction_method="REGEX", provenance=prov),
            ExtractedFact(type=FactType.CURRENCY, value="USD", confidence=1.0, extraction_method="REGEX", provenance=prov),
        ]
    )
    
    results = evaluate_requirements(case, [ev], reqs)
    payment_verif = next((r for r in results if r.id == "visa_10_4_payment_verification"), None)
    assert payment_verif is not None
    assert payment_verif.status == RequirementStatus.SATISFIED
    
def test_ce30_matcher():
    case = DisputeCase(merchant_id="m1", transaction_id="t1", amount=100.0, currency="USD", network=CardNetwork.VISA, reason_code="10.4")
    prov = Provenance(source_file="test", source_location="1", content_hash="hash")
    
    # Disputed evidence
    ev1 = EvidenceItem(
        case_id=case.id,
        source_type="OTHER",
        semantic_type=EvidenceType.PAYMENT_PROOF,
        extracted_facts=[
            ExtractedFact(type=FactType.IP_ADDRESS, value="192.168.1.1", confidence=1.0, extraction_method="REGEX", provenance=prov),
        ]
    )
    
    # Historical evidence 1 (150 days ago)
    date1 = (case.created_at - timedelta(days=150)).isoformat()
    ev2 = EvidenceItem(
        case_id=case.id,
        source_type="OTHER",
        semantic_type=EvidenceType.HISTORICAL_MATCH,
        extracted_facts=[
            ExtractedFact(type=FactType.TIMESTAMP, value=date1, confidence=1.0, extraction_method="REGEX", provenance=prov),
            ExtractedFact(type=FactType.IP_ADDRESS, value="192.168.1.1", confidence=1.0, extraction_method="REGEX", provenance=prov),
        ]
    )
    
    # Historical evidence 2 (200 days ago)
    date2 = (case.created_at - timedelta(days=200)).isoformat()
    ev3 = EvidenceItem(
        case_id=case.id,
        source_type="OTHER",
        semantic_type=EvidenceType.HISTORICAL_MATCH,
        extracted_facts=[
            ExtractedFact(type=FactType.TIMESTAMP, value=date2, confidence=1.0, extraction_method="REGEX", provenance=prov),
            ExtractedFact(type=FactType.IP_ADDRESS, value="192.168.1.1", confidence=1.0, extraction_method="REGEX", provenance=prov),
        ]
    )
    
    res = evaluate_ce30(case, [ev1, ev2, ev3])
    assert res.qualified is True
    assert 'IP' in res.matching_elements

def test_scoring_strong_evidence():
    reqs = [
        Requirement(id="visa_10_4_payment_verification", name="Payment Verification", description="desc", status=RequirementStatus.SATISFIED, source_reference="ref"),
        Requirement(id="visa_10_4_identity_linkage", name="Identity Linkage", description="desc", status=RequirementStatus.SATISFIED, source_reference="ref"),
        Requirement(id="visa_10_4_proof_of_digital_access", name="Proof of Access", description="desc", status=RequirementStatus.SATISFIED, source_reference="ref")
    ]
    
    score = score_evidence(reqs, None, [])
    assert score.total_score >= 60
    assert score.recommendation in [Recommendation.CONTEST, Recommendation.REVIEW]

def test_scoring_with_contradiction():
    reqs = [
        Requirement(id="visa_10_4_payment_verification", name="Payment Verification", description="desc", status=RequirementStatus.SATISFIED, source_reference="ref"),
    ]
    
    contra = Contradiction(description="IP mismatch", severity="HIGH", type="IP_MISMATCH")
    
    score = score_evidence(reqs, None, [contra])
    assert score.recommendation == Recommendation.REVIEW
