"""Unit tests for the deterministic verification and scoring engine.

These tests pin the *rebuilt* engine contract. Two of them were updated when the
engine was hardened and must now construct inputs the real pipeline actually
produces:

* **CE 3.0** now requires two or more matching data elements (one an IP/Device
  anchor) per historical transaction — not just one. The test therefore gives
  the disputed and historical transactions a shared IP *and* email.
* **Scoring** is now strength-weighted *coverage*, so a ``SATISFIED`` requirement
  only earns points when its ``coverage`` is populated (the requirement engine
  always sets it; a hand-built requirement must set it too).

See ``docs/evaluation.md`` for the before/after rationale.
"""

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
    # CE 3.0 requires each qualifying historical transaction to share >= 2 data
    # elements with the disputed transaction, at least one being an IP/Device
    # anchor. The disputed transaction therefore exposes IP + email, and each
    # historical transaction matches both.
    case = DisputeCase(merchant_id="m1", transaction_id="t1", amount=100.0, currency="USD", network=CardNetwork.VISA, reason_code="10.4")
    prov = Provenance(source_file="test", source_location="1", content_hash="hash")

    # Disputed transaction: IP + email (two matchable elements, one an anchor).
    ev1 = EvidenceItem(
        case_id=case.id,
        source_type="OTHER",
        semantic_type=EvidenceType.PAYMENT_PROOF,
        extracted_facts=[
            ExtractedFact(type=FactType.IP_ADDRESS, value="192.168.1.1", confidence=1.0, extraction_method="REGEX", provenance=prov),
            ExtractedFact(type=FactType.EMAIL_ADDRESS, value="user@example.com", confidence=1.0, extraction_method="REGEX", provenance=prov),
        ]
    )

    # Historical transaction 1 (150 days ago) — matches IP + email.
    date1 = (case.created_at - timedelta(days=150)).isoformat()
    ev2 = EvidenceItem(
        case_id=case.id,
        source_type="OTHER",
        semantic_type=EvidenceType.HISTORICAL_MATCH,
        extracted_facts=[
            ExtractedFact(type=FactType.TIMESTAMP, value=date1, confidence=1.0, extraction_method="REGEX", provenance=prov),
            ExtractedFact(type=FactType.IP_ADDRESS, value="192.168.1.1", confidence=1.0, extraction_method="REGEX", provenance=prov),
            ExtractedFact(type=FactType.EMAIL_ADDRESS, value="user@example.com", confidence=1.0, extraction_method="REGEX", provenance=prov),
        ]
    )

    # Historical transaction 2 (200 days ago) — matches IP + email.
    date2 = (case.created_at - timedelta(days=200)).isoformat()
    ev3 = EvidenceItem(
        case_id=case.id,
        source_type="OTHER",
        semantic_type=EvidenceType.HISTORICAL_MATCH,
        extracted_facts=[
            ExtractedFact(type=FactType.TIMESTAMP, value=date2, confidence=1.0, extraction_method="REGEX", provenance=prov),
            ExtractedFact(type=FactType.IP_ADDRESS, value="192.168.1.1", confidence=1.0, extraction_method="REGEX", provenance=prov),
            ExtractedFact(type=FactType.EMAIL_ADDRESS, value="user@example.com", confidence=1.0, extraction_method="REGEX", provenance=prov),
        ]
    )

    res = evaluate_ce30(case, [ev1, ev2, ev3])
    assert res.qualified is True
    assert 'IP' in res.matching_elements
    assert len(res.qualifying_transactions) == 2

def test_scoring_strong_evidence():
    # A genuinely strong case: the requirement engine reports these as SATISFIED
    # with full coverage. Scoring is strength-weighted coverage, so coverage
    # must be set (the engine always sets it; a hand-built requirement must too).
    reqs = [
        Requirement(id="visa_10_4_payment_verification", name="Payment Verification", description="desc", status=RequirementStatus.SATISFIED, source_reference="ref", strength="REQUIRED", coverage=1.0),
        Requirement(id="visa_10_4_identity_linkage", name="Identity Linkage", description="desc", status=RequirementStatus.SATISFIED, source_reference="ref", strength="STRONG", coverage=1.0),
        Requirement(id="visa_10_4_proof_of_digital_access", name="Proof of Access", description="desc", status=RequirementStatus.SATISFIED, source_reference="ref", strength="STRONG", coverage=1.0),
    ]

    score = score_evidence(reqs, None, [])
    assert score.total_score >= 60
    assert score.recommendation in [Recommendation.CONTEST, Recommendation.REVIEW]

def test_scoring_with_contradiction():
    # Even fully-covered evidence must be routed to human REVIEW when a
    # contradiction is present — the contradiction override is the point here.
    reqs = [
        Requirement(id="visa_10_4_payment_verification", name="Payment Verification", description="desc", status=RequirementStatus.SATISFIED, source_reference="ref", strength="REQUIRED", coverage=1.0),
    ]

    contra = Contradiction(description="IP mismatch", severity="HIGH", type="IP_MISMATCH")

    score = score_evidence(reqs, None, [contra])
    assert score.recommendation == Recommendation.REVIEW
