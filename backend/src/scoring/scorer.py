from typing import List, Optional
from src.domain.enums import RequirementStatus, Recommendation, ScoringFactorType
from src.domain.models import EvidenceScore, Requirement, Contradiction, ScoringFactor
from src.verification.ce30_matcher import CE30Result

def score_evidence(requirements: List[Requirement], ce30_result: Optional[CE30Result], contradictions: List[Contradiction]) -> EvidenceScore:
    """Transparent evidence strength scorer.
    
    Args:
        requirements: Evaluated requirements
        ce30_result: Result of CE 3.0 evaluation
        contradictions: List of contradictions found
        
    Returns:
        EvidenceScore object mapping total score to Recommendation
    """
    factors = []
    total = 0.0
    
    req_map = {r.id: r for r in requirements}
    
    def check_req(req_id: str, pts: int, name: str):
        nonlocal total
        if req_id in req_map:
            req = req_map[req_id]
            if req.status == RequirementStatus.SATISFIED:
                factors.append(ScoringFactor(
                    name=name, 
                    type=ScoringFactorType.POSITIVE, 
                    points=pts, 
                    description="Requirement Satisfied", 
                    evidence_ids=req.evidence_candidates
                ))
                total += pts
            elif req.status == RequirementStatus.MISSING and hasattr(req, 'strength') and req.strength == "REQUIRED":
                factors.append(ScoringFactor(
                    name=f"Missing {name}", 
                    type=ScoringFactorType.MISSING, 
                    points=-10, 
                    description="Required evidence is missing", 
                    evidence_ids=[]
                ))
                total -= 10
                
    # Positive points based on implementation plan
    check_req("visa_10_4_payment_verification", 20, "Payment Verification")
    check_req("visa_10_4_identity_linkage", 20, "Identity Linkage")
    check_req("visa_10_4_proof_of_digital_access", 20, "Proof of Access")
    check_req("visa_10_4_three_ds_authentication", 15, "3DS Authentication")
    
    check_req("mc_4837_device_identity", 20, "Device Identity")
    check_req("mc_4837_delivery_confirmation", 20, "Delivery Confirmation")
    check_req("mc_4837_identity_factor", 20, "Identity Factor")
    check_req("mc_4837_three_ds_authentication", 15, "3DS Authentication")
    
    check_req("visa_10_4_customer_communication", 5, "Customer Communication")
    check_req("mc_4837_customer_communication", 5, "Customer Communication")
    check_req("visa_10_4_terms_consent", 5, "Terms Consent")
    check_req("mc_4837_terms_consent", 5, "Terms Consent")
    check_req("visa_10_4_avs_cvv_verification", 3, "AVS/CVV")
    
    if ce30_result and ce30_result.qualified:
        factors.append(ScoringFactor(
            name="CE 3.0 Qualified", 
            type=ScoringFactorType.POSITIVE, 
            points=15, 
            description=ce30_result.reason, 
            evidence_ids=ce30_result.qualifying_transactions
        ))
        total += 15
        
    for i, contra in enumerate(contradictions):
        e_ids = []
        if contra.evidence_a_id: e_ids.append(contra.evidence_a_id)
        if contra.evidence_b_id: e_ids.append(contra.evidence_b_id)
        
        factors.append(ScoringFactor(
            name=f"Contradiction Found", 
            type=ScoringFactorType.NEGATIVE, 
            points=-15, 
            description=contra.description, 
            evidence_ids=e_ids
        ))
        total -= 15
        
    # Apply total limits (0-100)
    total = max(0, min(100, total))
    
    rec = Recommendation.ABSTAIN
    if contradictions:
        rec = Recommendation.REVIEW
    elif total >= 75:
        rec = Recommendation.CONTEST
    elif total >= 50:
        rec = Recommendation.REVIEW
    elif total >= 25:
        rec = Recommendation.INSUFFICIENT
        
    return EvidenceScore(total_score=total, factors=factors, recommendation=rec)
