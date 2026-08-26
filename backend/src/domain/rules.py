from typing import List

from pydantic import BaseModel, Field

from src.domain.enums import CardNetwork, EvidenceType, FactType


class RequirementDefinition(BaseModel):
    """Defines a rule or requirement from a card network."""
    id: str = Field(description="Unique identifier for this requirement definition")
    name: str = Field(description="Human-readable name")
    description: str = Field(description="Detailed description of what is needed")
    required_evidence_types: List[EvidenceType] = Field(description="Types of evidence that can satisfy this")
    required_fact_types: List[FactType] = Field(description="Specific facts that must be extracted")
    strength: str = Field(description="Strength of the requirement: REQUIRED, STRONG, SUPPORTING")
    source_reference: str = Field(description="Citation to the card network rules")
    is_auto_win: bool = Field(default=False, description="Whether satisfying this is an automatic win")


# Visa Reason Code 10.4 Requirements (Fraud - Card Absent)
VISA_10_4_REQUIREMENTS = [
    RequirementDefinition(
        id="visa_10_4_payment_verification",
        name="Payment Verification",
        description="Proof that the transaction was authorized and settled.",
        required_evidence_types=[EvidenceType.PAYMENT_PROOF],
        required_fact_types=[FactType.PAYMENT_ID, FactType.AMOUNT, FactType.CURRENCY],
        strength="REQUIRED",
        source_reference="Visa Core Rules v2024, Section 11.1.4",
    ),
    RequirementDefinition(
        id="visa_10_4_identity_linkage",
        name="Identity Linkage",
        description="Link between the purchaser and the cardholder (IP, Device ID).",
        required_evidence_types=[EvidenceType.IDENTITY_PROOF, EvidenceType.AUTHENTICATION_PROOF],
        required_fact_types=[FactType.IP_ADDRESS, FactType.DEVICE_ID],
        strength="STRONG",
        source_reference="Visa Core Rules v2024, Section 11.1.4",
    ),
    RequirementDefinition(
        id="visa_10_4_proof_of_digital_access",
        name="Proof of Digital Access",
        description="Evidence that the customer downloaded or accessed the digital goods.",
        required_evidence_types=[EvidenceType.ACCESS_PROOF, EvidenceType.DELIVERY_PROOF],
        required_fact_types=[FactType.TIMESTAMP, FactType.IP_ADDRESS, FactType.ACCOUNT_ID],
        strength="STRONG",
        source_reference="Visa Core Rules v2024, Section 11.1.4",
    ),
    RequirementDefinition(
        id="visa_10_4_three_ds_authentication",
        name="3DS Authentication",
        description="Proof of 3D Secure authentication with liability shift.",
        required_evidence_types=[EvidenceType.AUTHENTICATION_PROOF],
        required_fact_types=[FactType.ECI_VALUE, FactType.CAVV, FactType.DS_TRANS_ID],
        strength="REQUIRED",
        source_reference="Visa Core Rules v2024, Section 11.1.4",
        is_auto_win=True,
    ),
    RequirementDefinition(
        id="visa_10_4_ce30_historical_match",
        name="CE 3.0 Historical Match",
        description="2 prior undisputed transactions between 120-365 days with matching IP/Device.",
        required_evidence_types=[EvidenceType.HISTORICAL_MATCH],
        required_fact_types=[FactType.PAYMENT_ID, FactType.IP_ADDRESS, FactType.DEVICE_ID],
        strength="STRONG",
        source_reference="Visa Core Rules v2024, Section 11.1.4 (CE 3.0)",
        is_auto_win=True,
    ),
    RequirementDefinition(
        id="visa_10_4_customer_communication",
        name="Customer Communication",
        description="Support interactions or emails showing the customer used the product.",
        required_evidence_types=[EvidenceType.COMMUNICATION],
        required_fact_types=[FactType.EMAIL_ADDRESS, FactType.CUSTOMER_NAME],
        strength="SUPPORTING",
        source_reference="Visa Core Rules v2024, Section 11.1.4",
    ),
    RequirementDefinition(
        id="visa_10_4_terms_consent",
        name="Terms Consent",
        description="Proof the cardholder accepted the terms of service.",
        required_evidence_types=[EvidenceType.POLICY_DOCUMENT],
        required_fact_types=[FactType.TIMESTAMP, FactType.IP_ADDRESS],
        strength="SUPPORTING",
        source_reference="Visa Core Rules v2024, Section 11.1.4",
    ),
    RequirementDefinition(
        id="visa_10_4_avs_cvv_verification",
        name="AVS/CVV Verification",
        description="Address and CVV match at the time of transaction.",
        required_evidence_types=[EvidenceType.PAYMENT_PROOF],
        required_fact_types=[FactType.AVS_RESULT, FactType.CVV_RESULT],
        strength="SUPPORTING",
        source_reference="Visa Core Rules v2024, Section 11.1.4",
    ),
]


# Mastercard Reason Code 4837 Requirements (No Cardholder Authorization)
MASTERCARD_4837_REQUIREMENTS = [
    RequirementDefinition(
        id="mc_4837_device_identity",
        name="Device Identity (FPT Category 1)",
        description="Compelling evidence of device identity (IP, Device ID, Fingerprint).",
        required_evidence_types=[EvidenceType.IDENTITY_PROOF],
        required_fact_types=[FactType.IP_ADDRESS, FactType.DEVICE_ID, FactType.DEVICE_FINGERPRINT],
        strength="STRONG",
        source_reference="Mastercard Chargeback Guide v2024, Section 3.2 (4837)",
    ),
    RequirementDefinition(
        id="mc_4837_delivery_confirmation",
        name="Delivery Confirmation (FPT Category 2)",
        description="Proof of delivery or access (download log, email delivery).",
        required_evidence_types=[EvidenceType.DELIVERY_PROOF, EvidenceType.ACCESS_PROOF],
        required_fact_types=[FactType.TIMESTAMP, FactType.EMAIL_ADDRESS, FactType.ACCOUNT_ID],
        strength="STRONG",
        source_reference="Mastercard Chargeback Guide v2024, Section 3.2 (4837)",
    ),
    RequirementDefinition(
        id="mc_4837_identity_factor",
        name="Identity Factor (FPT Category 3)",
        description="Login, MFA, or verified contact information.",
        required_evidence_types=[EvidenceType.AUTHENTICATION_PROOF],
        required_fact_types=[FactType.SESSION_ID, FactType.TIMESTAMP],
        strength="STRONG",
        source_reference="Mastercard Chargeback Guide v2024, Section 3.2 (4837)",
    ),
    RequirementDefinition(
        id="mc_4837_three_ds_authentication",
        name="3DS Authentication",
        description="Proof of 3D Secure authentication with liability shift.",
        required_evidence_types=[EvidenceType.AUTHENTICATION_PROOF],
        required_fact_types=[FactType.ECI_VALUE, FactType.CAVV],
        strength="REQUIRED",
        source_reference="Mastercard Chargeback Guide v2024, Section 3.2 (4837)",
        is_auto_win=True,
    ),
    RequirementDefinition(
        id="mc_4837_customer_communication",
        name="Customer Communication",
        description="Support interactions or emails showing the customer used the product.",
        required_evidence_types=[EvidenceType.COMMUNICATION],
        required_fact_types=[FactType.EMAIL_ADDRESS, FactType.CUSTOMER_NAME],
        strength="SUPPORTING",
        source_reference="Mastercard Chargeback Guide v2024, Section 3.2 (4837)",
    ),
    RequirementDefinition(
        id="mc_4837_terms_consent",
        name="Terms Consent",
        description="Proof the cardholder accepted the terms of service.",
        required_evidence_types=[EvidenceType.POLICY_DOCUMENT],
        required_fact_types=[FactType.TIMESTAMP, FactType.IP_ADDRESS],
        strength="SUPPORTING",
        source_reference="Mastercard Chargeback Guide v2024, Section 3.2 (4837)",
    ),
]


def get_requirements(card_network: CardNetwork, reason_code: str) -> List[RequirementDefinition]:
    """
    Get the appropriate requirement list based on card network and reason code.
    
    Args:
        card_network: The card network (e.g., VISA, MASTERCARD).
        reason_code: The reason code (e.g., '10.4', '4837').
        
    Returns:
        List[RequirementDefinition]: The rules for this dispute type.
    """
    if card_network == CardNetwork.VISA and reason_code == "10.4":
        return VISA_10_4_REQUIREMENTS
    elif card_network == CardNetwork.MASTERCARD and reason_code == "4837":
        return MASTERCARD_4837_REQUIREMENTS
    
    # Return empty list or raise an exception if not found
    return []
