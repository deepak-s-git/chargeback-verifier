from typing import List, Any
from datetime import datetime, timezone
from pydantic import BaseModel
from src.domain.enums import FactType, EvidenceType
from src.domain.models import DisputeCase, EvidenceItem
from src.ingestion.normalizer import normalize_timestamp

class CE30Result(BaseModel):
    qualified: bool
    matching_elements: List[str]
    qualifying_transactions: List[str]
    reason: str

def evaluate_ce30(disputed_txn: DisputeCase, evidence_items: List[EvidenceItem]) -> CE30Result:
    """Visa CE 3.0 rule engine.
    
    Checks for historical transactions between 120-365 days prior with matching IP/Device.
    
    Args:
        disputed_txn: The dispute case
        evidence_items: List of evidence items
        
    Returns:
        CE30Result object
    """
    historical_items = [e for e in evidence_items if e.semantic_type == EvidenceType.HISTORICAL_MATCH]
    
    if not historical_items:
        return CE30Result(qualified=False, matching_elements=[], qualifying_transactions=[], reason="No historical transactions provided")
        
    # We need to find the disputed transaction's IP, device_id, account_id from its own evidence
    disputed_facts = {}
    for e in evidence_items:
        if e.semantic_type != EvidenceType.HISTORICAL_MATCH:
            for fact in e.extracted_facts:
                if fact.type not in disputed_facts:
                    disputed_facts[fact.type] = set()
                disputed_facts[fact.type].add(fact.value)
                
    disputed_date = disputed_txn.created_at
    
    qualifying_txns = []
    matching_elements_overall = set()
    
    for hist in historical_items:
        hist_date_str = None
        hist_facts = {}
        for fact in hist.extracted_facts:
            if fact.type == FactType.TIMESTAMP:
                hist_date_str = fact.value
            if fact.type not in hist_facts:
                hist_facts[fact.type] = set()
            hist_facts[fact.type].add(fact.value)
            
        if not hist_date_str:
            continue
            
        try:
            hist_date = normalize_timestamp(hist_date_str)
            if not hist_date:
                continue
        except Exception:
            continue
            
        # Ensure timezone aware
        if hist_date.tzinfo is None:
            hist_date = hist_date.replace(tzinfo=timezone.utc)
        disputed_date_tz = disputed_date
        if disputed_date_tz.tzinfo is None:
            disputed_date_tz = disputed_date_tz.replace(tzinfo=timezone.utc)
            
        days_diff = (disputed_date_tz - hist_date).days
        
        if 120 <= days_diff <= 365:
            matches = []
            if FactType.IP_ADDRESS in disputed_facts and FactType.IP_ADDRESS in hist_facts:
                if disputed_facts[FactType.IP_ADDRESS].intersection(hist_facts[FactType.IP_ADDRESS]):
                    matches.append('IP')
            if FactType.DEVICE_ID in disputed_facts and FactType.DEVICE_ID in hist_facts:
                if disputed_facts[FactType.DEVICE_ID].intersection(hist_facts[FactType.DEVICE_ID]):
                    matches.append('DeviceID')
            if FactType.ACCOUNT_ID in disputed_facts and FactType.ACCOUNT_ID in hist_facts:
                if disputed_facts[FactType.ACCOUNT_ID].intersection(hist_facts[FactType.ACCOUNT_ID]):
                    matches.append('AccountID')
                    
            if ('IP' in matches or 'DeviceID' in matches) and len(matches) > 0:
                qualifying_txns.append(hist.id)
                matching_elements_overall.update(matches)
                
    if len(qualifying_txns) >= 2:
        return CE30Result(
            qualified=True, 
            matching_elements=list(matching_elements_overall), 
            qualifying_transactions=qualifying_txns, 
            reason="Found 2+ valid historical transactions with matching IP or Device ID"
        )
        
    return CE30Result(
        qualified=False, 
        matching_elements=list(matching_elements_overall), 
        qualifying_transactions=qualifying_txns, 
        reason=f"Found only {len(qualifying_txns)} valid historical transactions (need 2+)"
    )
