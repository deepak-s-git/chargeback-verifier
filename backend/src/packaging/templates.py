from typing import List, Dict
from pydantic import BaseModel
from src.domain.enums import CardNetwork

class PackageTemplate(BaseModel):
    card_network: CardNetwork
    reason_code: str
    sections: List[str]
    formatting_rules: Dict[str, str]

def get_template(card_network: CardNetwork, reason_code: str) -> PackageTemplate:
    """Get formatting template based on network and reason code."""
    if card_network == CardNetwork.VISA and reason_code == "10.4":
        return PackageTemplate(
            card_network=card_network,
            reason_code=reason_code,
            sections=[
                "Executive Summary",
                "Transaction Details",
                "Identity Verification",
                "3DS Authentication",
                "Digital Delivery Proof",
                "Usage Timeline",
                "Terms Consent",
                "CE 3.0 Data"
            ],
            formatting_rules={"citation": "brackets", "max_length": "5000"}
        )
    elif card_network == CardNetwork.MASTERCARD and reason_code == "4837":
        return PackageTemplate(
            card_network=card_network,
            reason_code=reason_code,
            sections=[
                "Executive Summary",
                "FPT Validation",
                "Transaction Details",
                "Identity Verification",
                "3DS Authentication",
                "Digital Delivery Proof",
                "Usage Timeline",
                "Terms Consent"
            ],
            formatting_rules={"citation": "brackets", "max_length": "5000"}
        )
    else:
        # Default template
        return PackageTemplate(
            card_network=card_network,
            reason_code=reason_code,
            sections=[
                "Executive Summary",
                "Transaction Details",
                "Defense Claims",
                "Timeline",
                "Conclusion"
            ],
            formatting_rules={"citation": "brackets"}
        )
