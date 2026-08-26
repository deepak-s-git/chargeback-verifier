"""Transparent, calibrated evidence scoring.

The previous scorer awarded hardcoded per-requirement points, gave nothing for
partially satisfied requirements, penalised strong cases for lacking optional
auto-win evidence, and topped out below the contest threshold — so even a
genuinely complete case scored as "review" or worse. This rewrite scores on a
principled basis:

* **Strength-weighted coverage.** Each requirement contributes
  ``weight × coverage`` where weight reflects how much the network cares
  (``REQUIRED`` = 3, ``STRONG`` = 2, ``SUPPORTING`` = 1). Partial coverage earns
  partial credit.
* **Normalised to what is achievable.** The base score is the percentage of the
  total *non-auto-win* weight that the evidence actually covers, so it is a
  network-agnostic 0-100 "% of achievable strength".
* **Auto-win liability shifts.** A satisfied 3-D Secure requirement or a
  qualifying CE 3.0 history is, in practice, decisive — it lifts the score to at
  least 90 rather than being folded into the average (and its absence is *not*
  penalised).
* **Defense-first gating.** Detected contradictions or prompt injection force
  the recommendation down to ``REVIEW`` — the system never auto-contests
  something a human should adjudicate — and a wholly missing *required*
  foundation caps the recommendation at ``REVIEW`` as well.

Every input to the score is emitted as a :class:`ScoringFactor` so the number is
fully explainable in the UI and the audit trail.
"""

from typing import List, Optional

from src.domain.enums import Recommendation, RequirementStatus, ScoringFactorType
from src.domain.models import Contradiction, EvidenceScore, Requirement, ScoringFactor
from src.verification.ce30_matcher import CE30Result

# How much each requirement strength counts toward the achievable total.
STRENGTH_WEIGHTS = {"REQUIRED": 3.0, "STRONG": 2.0, "SUPPORTING": 1.0}

# Score a decisive liability shift (3DS / CE 3.0) guarantees.
AUTO_WIN_FLOOR = 90.0
# Display penalty applied to the numeric score per contradiction (recommendation
# is independently forced to REVIEW regardless of the number).
CONTRADICTION_PENALTY = 15.0

# Recommendation thresholds on the 0-100 scale.
CONTEST_THRESHOLD = 75.0
REVIEW_THRESHOLD = 50.0
INSUFFICIENT_THRESHOLD = 25.0

# Ordering used to "cap" (downgrade only) a recommendation.
_REC_RANK = {
    Recommendation.ABSTAIN: 0,
    Recommendation.INSUFFICIENT: 1,
    Recommendation.REVIEW: 2,
    Recommendation.CONTEST: 3,
}
_RANK_REC = {v: k for k, v in _REC_RANK.items()}


def _band(score: float) -> Recommendation:
    if score >= CONTEST_THRESHOLD:
        return Recommendation.CONTEST
    if score >= REVIEW_THRESHOLD:
        return Recommendation.REVIEW
    if score >= INSUFFICIENT_THRESHOLD:
        return Recommendation.INSUFFICIENT
    return Recommendation.ABSTAIN


def _cap(rec: Recommendation, ceiling: Recommendation) -> Recommendation:
    """Downgrade ``rec`` to at most ``ceiling`` (never promotes)."""
    return _RANK_REC[min(_REC_RANK[rec], _REC_RANK[ceiling])]


def score_evidence(
    requirements: List[Requirement],
    ce30_result: Optional[CE30Result],
    contradictions: List[Contradiction],
    injection_detected: bool = False,
) -> EvidenceScore:
    """Compute the calibrated evidence score and recommendation.

    Args:
        requirements: Evaluated requirements (with coverage populated).
        ce30_result: The CE 3.0 evaluation, if applicable.
        contradictions: Contradictions detected across the evidence.
        injection_detected: Whether prompt injection was found in any evidence.

    Returns:
        An :class:`EvidenceScore` with a transparent factor breakdown and a
        defense-first recommendation.
    """
    factors: List[ScoringFactor] = []

    # --- Base: strength-weighted coverage over non-auto-win requirements ------
    base_reqs = [r for r in requirements if not r.is_auto_win]
    denom = sum(STRENGTH_WEIGHTS.get(r.strength, 1.0) for r in base_reqs) or 1.0

    base = 0.0
    required_fully_missing = False
    for r in base_reqs:
        weight = STRENGTH_WEIGHTS.get(r.strength, 1.0)
        effective_coverage = 0.0 if r.status == RequirementStatus.CONTRADICTED else r.coverage
        contribution = 100.0 * weight * effective_coverage / denom
        base += contribution

        if contribution > 0:
            factors.append(
                ScoringFactor(
                    name=r.name,
                    type=ScoringFactorType.POSITIVE,
                    points=round(contribution, 1),
                    description=(
                        f"{r.status.value} — {r.coverage:.0%} coverage "
                        f"(strength: {r.strength.title()})"
                    ),
                    evidence_ids=r.evidence_candidates,
                )
            )
        elif r.status == RequirementStatus.MISSING and r.strength in ("REQUIRED", "STRONG"):
            factors.append(
                ScoringFactor(
                    name=f"Missing: {r.name}",
                    type=ScoringFactorType.MISSING,
                    points=0.0,
                    description=(
                        f"No supporting evidence found. Missing fact types: "
                        f"{', '.join(r.missing_fact_types) or 'evidence of the required type'}."
                    ),
                    evidence_ids=[],
                )
            )
        if r.strength == "REQUIRED" and r.status == RequirementStatus.MISSING:
            required_fully_missing = True

    score = base

    # --- Auto-win liability shift (3DS or CE 3.0) -----------------------------
    three_ds_win = any(
        r.is_auto_win and "three_ds" in r.id and r.status == RequirementStatus.SATISFIED
        for r in requirements
    )
    ce30_win = bool(ce30_result and ce30_result.qualified)
    if three_ds_win or ce30_win:
        boosted = max(base, AUTO_WIN_FLOOR)
        reason = (
            "Qualifying CE 3.0 transaction history (liability shift)"
            if ce30_win
            else "3-D Secure authentication with liability shift"
        )
        ev_ids = ce30_result.qualifying_transactions if ce30_win and ce30_result else []
        factors.append(
            ScoringFactor(
                name="Liability Shift",
                type=ScoringFactorType.POSITIVE,
                points=round(boosted - base, 1),
                description=f"{reason} — decisive under network rules.",
                evidence_ids=ev_ids,
            )
        )
        score = boosted

    # --- Contradictions: numeric penalty + (later) forced review --------------
    for contra in contradictions:
        ev_ids = [i for i in (contra.evidence_a_id, contra.evidence_b_id) if i]
        factors.append(
            ScoringFactor(
                name=f"Contradiction: {contra.type}",
                type=ScoringFactorType.NEGATIVE,
                points=-CONTRADICTION_PENALTY,
                description=contra.description,
                evidence_ids=ev_ids,
            )
        )
        score -= CONTRADICTION_PENALTY

    if injection_detected:
        factors.append(
            ScoringFactor(
                name="Prompt Injection Detected",
                type=ScoringFactorType.NEGATIVE,
                points=0.0,
                description=(
                    "Evidence contains prompt-injection patterns; treated as untrusted data and "
                    "routed to human review. It cannot drive an automated contest."
                ),
                evidence_ids=[],
            )
        )

    score = max(0.0, min(100.0, score))

    # --- Recommendation with defense-first caps -------------------------------
    rec = _band(score)
    if required_fully_missing:
        rec = _cap(rec, Recommendation.REVIEW)
    if contradictions:
        rec = Recommendation.REVIEW  # a detected contradiction always needs a human
    if injection_detected:
        rec = Recommendation.REVIEW  # untrusted content must be adjudicated by a human

    return EvidenceScore(total_score=round(score, 1), factors=factors, recommendation=rec)
