"""Run the DisputeShield decision system over a single case for evaluation.

Two modes let the evaluation quantify what the full pipeline contributes:

* ``full`` — the real production decision core, :func:`analyze_evidence`. This
  is the system under test: requirement evaluation, CE 3.0 matching,
  contradiction detection, prompt-injection screening, claim grounding, scoring
  and the human-review gate, all together.
* ``partial`` — an *ablation*: deterministic requirement scoring only, with CE
  3.0, contradictions and injection overrides disabled (``score_evidence(reqs,
  None, [])``). This mirrors the pre-rewrite baseline and isolates the value the
  defensive/CE 3.0 layers add on the *same* coherent dataset.

Both modes return the same :class:`Prediction` shape so the metrics layer can
score them identically.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict

from src.domain.models import DisputeCase
from src.domain.rules import get_requirements
from src.orchestrator.analysis import analyze_evidence
from src.scoring.scorer import score_evidence
from src.verification.requirement_engine import evaluate_requirements

FULL = "full"
PARTIAL = "partial"


@dataclass
class Prediction:
    case_id: str
    recommendation: str  # CONTEST / REVIEW / INSUFFICIENT / ABSTAIN
    score: float
    contradictions: int
    injection: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _predict_full(case: DisputeCase) -> Prediction:
    result = analyze_evidence(case, case.evidence_items)
    return Prediction(
        case_id=case.id,
        recommendation=result.score.recommendation.value,
        score=round(result.score.total_score, 2),
        contradictions=len(result.contradictions),
        injection=result.injection_detected,
    )


def _predict_partial(case: DisputeCase) -> Prediction:
    """Ablation: requirement scoring with the CE 3.0 / defensive layers removed."""
    requirements_def = get_requirements(case.network, case.reason_code)
    eval_reqs = evaluate_requirements(case, case.evidence_items, requirements_def)
    score = score_evidence(eval_reqs, None, [])
    return Prediction(
        case_id=case.id,
        recommendation=score.recommendation.value,
        score=round(score.total_score, 2),
        contradictions=0,
        injection=False,
    )


def predict(case: DisputeCase, mode: str = FULL) -> Prediction:
    """Produce a :class:`Prediction` for ``case`` under ``mode`` (``full`` | ``partial``)."""
    if mode == FULL:
        return _predict_full(case)
    if mode == PARTIAL:
        return _predict_partial(case)
    raise ValueError(f"unknown prediction mode {mode!r} (expected {FULL!r} or {PARTIAL!r})")
