from typing import Protocol, Dict, Any
from src.domain.models import DisputeCase

class ChargebackProvider(Protocol):
    """Protocol for chargeback providers (e.g., Razorpay, Stripe)."""
    
    async def get_dispute(self, dispute_id: str) -> DisputeCase:
        ...
        
    async def submit_evidence(self, dispute_id: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
        ...
