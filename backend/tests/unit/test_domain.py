import pytest

from src.domain.enums import CardNetwork, EvidenceType, FactType, DisputeCategory
from src.domain.models import (
    Claim,
    DisputeCase,
    EvidenceItem,
    Provenance,
)
from src.domain.rules import get_requirements, RequirementDefinition


def test_dispute_case_creation_and_id_format():
    case = DisputeCase(
        merchant_id="merch_123",
        transaction_id="txn_abc",
        amount=99.99,
        currency="USD",
        network=CardNetwork.VISA,
        reason_code="10.4",
        category=DisputeCategory.FRAUD_UNAUTHORIZED,
    )
    assert case.id.startswith("CASE-")
    assert case.merchant_id == "merch_123"
    assert case.network == CardNetwork.VISA


def test_invalid_case_id():
    with pytest.raises(ValueError, match="Case ID must start with CASE-"):
        DisputeCase(
            id="INVALID-123",
            merchant_id="merch_123",
            transaction_id="txn_abc",
            amount=99.99,
            currency="USD",
            network=CardNetwork.VISA,
            reason_code="10.4"
        )


def test_evidence_item_id_format():
    evidence = EvidenceItem(
        case_id="CASE-123",
        source_type="PDF_DOCUMENT",
        semantic_type="PAYMENT_PROOF"
    )
    assert evidence.id.startswith("EV-")


def test_claim_id_format():
    claim = Claim(
        description="User matched IP address."
    )
    assert claim.id.startswith("CLM-")


def test_provenance_hash_computation():
    content = "The IP address was 192.168.1.1"
    hash_val = Provenance.compute_hash(content)
    # Check that it produces a valid SHA-256 hex string (64 characters)
    assert len(hash_val) == 64
    assert isinstance(hash_val, str)


def test_get_requirements_visa_10_4():
    reqs = get_requirements(CardNetwork.VISA, "10.4")
    assert len(reqs) > 0
    assert any(r.id == "visa_10_4_payment_verification" for r in reqs)
    
    # Check that 3DS is an auto win
    three_ds = next(r for r in reqs if r.id == "visa_10_4_three_ds_authentication")
    assert three_ds.is_auto_win is True


def test_get_requirements_mc_4837():
    reqs = get_requirements(CardNetwork.MASTERCARD, "4837")
    assert len(reqs) > 0
    assert any(r.id == "mc_4837_device_identity" for r in reqs)


def test_get_requirements_not_found():
    reqs = get_requirements(CardNetwork.VISA, "UNKNOWN_CODE")
    assert len(reqs) == 0


def test_requirement_definition_validation():
    req = RequirementDefinition(
        id="test_req",
        name="Test Req",
        description="A test requirement",
        required_evidence_types=[EvidenceType.PAYMENT_PROOF],
        required_fact_types=[FactType.AMOUNT],
        strength="REQUIRED",
        source_reference="Testing Guide"
    )
    assert req.id == "test_req"
    assert req.is_auto_win is False  # Default value
