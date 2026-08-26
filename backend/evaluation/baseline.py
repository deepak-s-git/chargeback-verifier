import json
from pathlib import Path
from typing import Dict, List, Any
from src.domain.models import DisputeCase
from src.domain.rules import get_requirements
from src.verification.requirement_engine import evaluate_requirements
from src.scoring.scorer import score_evidence

def run_baseline(case: DisputeCase) -> Dict[str, Any]:
    requirements_def = get_requirements(case.network, case.reason_code)
    eval_reqs = evaluate_requirements(case, case.evidence_items, requirements_def)
    
    # We do a deterministic run. No LLM contradictions or CE3.0 complex logic yet for baseline.
    score = score_evidence(eval_reqs, None, [])
    
    return {
        "case_id": case.id,
        "recommendation": score.recommendation,
        "score": score.total_score,
        "requirements": {r.name: r.status for r in eval_reqs}
    }
