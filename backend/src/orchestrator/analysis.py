"""Pure, side-effect-free case analysis.

This is the deterministic decision core of DisputeShield, factored out of
:class:`~src.orchestrator.case_service.CaseService` so that it has exactly one
implementation. The service calls it between a DB read and a DB write; the
offline evaluation harness calls it directly on in-memory cases. Because both
paths run *this* function, the evaluation measures the real system rather than a
reimplementation of it (the previous evaluation baseline silently ran a partial
engine with CE 3.0, contradictions and injection all disabled).

``analyze_evidence`` takes a case and its evidence and returns a
:class:`CaseAnalysisResult`. It performs no I/O: no database, no network, no LLM.
The only optional non-determinism in the whole system — LLM fact extraction —
happens earlier, during ingestion; by the time analysis runs, every fact is just
data to be grounded.
"""

from typing import List, Optional

from pydantic import BaseModel

from src.domain.enums import ClaimStatus, RequirementStatus
from src.domain.models import (
    Claim,
    Contradiction,
    DisputeCase,
    EvidenceItem,
    EvidenceScore,
    Requirement,
    TimelineEvent,
)
from src.domain.rules import get_requirements
from src.orchestrator.gate import GateResult, apply_gate
from src.scoring.scorer import score_evidence
from src.security.injection import detect_injection
from src.verification.ce30_matcher import CE30Result, evaluate_ce30
from src.verification.claim_verifier import verify_claim
from src.verification.contradiction import detect_contradictions
from src.verification.requirement_engine import evaluate_requirements
from src.verification.timeline_builder import build_timeline


class CaseAnalysisResult(BaseModel):
    """The complete, explainable output of analysing one case."""

    case: DisputeCase
    evidence: List[EvidenceItem]
    requirements: List[Requirement]
    timeline: List[TimelineEvent]
    ce30_result: Optional[CE30Result]
    contradictions: List[Contradiction]
    claims: List[Claim]
    score: EvidenceScore
    gate_result: GateResult
    injection_detected: bool = False
    injection_patterns: List[str] = []


def detect_injection_union(evidence_items: List[EvidenceItem]) -> List[str]:
    """Return the sorted union of prompt-injection patterns across evidence.

    Evidence is untrusted *data*: we never execute or obey it. Detection here
    only raises a flag that the scorer and the review gate consume to route the
    case to a human. Raw content is never logged from this function.
    """
    patterns: List[str] = []
    for item in evidence_items:
        if not item.raw_content:
            continue
        result = detect_injection(item.raw_content)
        if result.detected:
            patterns.extend(result.patterns_matched)
    return sorted(set(patterns))


def analyze_evidence(case: DisputeCase, evidence_items: List[EvidenceItem]) -> CaseAnalysisResult:
    """Run the full deterministic analysis for a case.

    Args:
        case: The dispute case (provides network, reason code, transaction date).
        evidence_items: All evidence gathered for the case, each fact already
            carrying provenance.

    Returns:
        A :class:`CaseAnalysisResult` with the timeline, requirement coverage,
        CE 3.0 verdict, contradictions, grounded claims, calibrated score, and
        the human-review gate decision. No side effects.
    """
    req_defs = get_requirements(case.network, case.reason_code)

    # --- Deterministic verification ------------------------------------------
    timeline = build_timeline(evidence_items)
    requirements = evaluate_requirements(case, evidence_items, req_defs)

    ce30_result: Optional[CE30Result] = None
    if case.network.value == "VISA":
        ce30_result = evaluate_ce30(case, evidence_items)

    contradictions = detect_contradictions(evidence_items, timeline, case)

    injection_patterns = detect_injection_union(evidence_items)
    injection_detected = bool(injection_patterns)

    score = score_evidence(requirements, ce30_result, contradictions, injection_detected)

    # --- Claim generation + cryptographic grounding --------------------------
    # A claim is minted only for a genuinely SATISFIED requirement, and only
    # survives if it can be grounded in the cited evidence (verify_claim).
    claims: List[Claim] = []
    for req in requirements:
        if req.status != RequirementStatus.SATISFIED:
            continue
        claim = Claim(
            description=f"{req.name} is satisfied per {req.source_reference}.",
            status=ClaimStatus.DRAFT,
            supporting_evidence_ids=list(req.evidence_candidates),
        )
        claims.append(verify_claim(claim, evidence_items))

    gate_result = apply_gate(score, contradictions, claims, injection_detected)

    return CaseAnalysisResult(
        case=case,
        evidence=evidence_items,
        requirements=requirements,
        timeline=timeline,
        ce30_result=ce30_result,
        contradictions=contradictions,
        claims=claims,
        score=score,
        gate_result=gate_result,
        injection_detected=injection_detected,
        injection_patterns=injection_patterns,
    )
