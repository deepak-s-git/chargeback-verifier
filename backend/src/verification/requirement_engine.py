from typing import List
from src.domain.enums import RequirementStatus
from src.domain.models import DisputeCase, EvidenceItem, Requirement
from src.domain.rules import RequirementDefinition

def evaluate_requirements(case: DisputeCase, evidence_items: List[EvidenceItem], requirements: List[RequirementDefinition]) -> List[Requirement]:
    """Deterministic requirement matcher.
    
    Args:
        case: The dispute case
        evidence_items: List of evidence items
        requirements: List of requirement definitions
        
    Returns:
        List of evaluated requirements with their status
    """
    results = []
    
    for req_def in requirements:
        matching_evidence_ids = []
        satisfied_types = set()
        satisfied_facts = set()
        
        for item in evidence_items:
            matches_type = item.semantic_type in req_def.required_evidence_types
            
            # Check if this item has any of the required facts
            item_fact_types = {fact.type for fact in item.extracted_facts}
            matching_facts = item_fact_types.intersection(req_def.required_fact_types)
            
            if matches_type or matching_facts:
                matching_evidence_ids.append(item.id)
                if matches_type:
                    satisfied_types.add(item.semantic_type)
                satisfied_facts.update(matching_facts)
                
        # Determine status
        if satisfied_types and satisfied_facts.issuperset(req_def.required_fact_types):
            status = RequirementStatus.SATISFIED
        elif satisfied_types or satisfied_facts:
            status = RequirementStatus.PARTIALLY_SATISFIED
        else:
            status = RequirementStatus.MISSING
            
        req = Requirement(
            id=req_def.id,
            name=req_def.name,
            description=req_def.description,
            status=status,
            evidence_candidates=matching_evidence_ids,
            source_reference=req_def.source_reference
        )
        results.append(req)
        
    return results
