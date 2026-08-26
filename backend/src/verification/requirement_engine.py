"""Deterministic requirement evaluation with partial credit.

For each :class:`RequirementDefinition` this computes a *coverage ratio* — how
much of the required evidence is actually present — rather than the previous
all-or-nothing ``issuperset`` test. Coverage distinguishes three tiers of
support:

* **Primary supporters** — evidence whose *semantic type* is one the
  requirement accepts (e.g. an ``ACCESS_PROOF`` item for "proof of digital
  access"). Facts found on primary supporters earn full credit.
* **Pooled facts** — required facts that appear only on *other* evidence
  items (e.g. an IP that shows up in a payment record but not an access log).
  These are circumstantial and earn half credit.
* **Missing facts** — required facts absent everywhere.

A requirement is ``SATISFIED`` only when a primary supporter exists *and* every
required fact is present on a primary supporter (coverage ``== 1.0``). Anything
in between is ``PARTIALLY_SATISFIED`` and earns proportional credit in the
scorer; nothing at all is ``MISSING``. This is what lets a genuinely strong
case reach a contest-worthy score while a case with gaps lands in the review
band — the calibration the old binary matcher could never express.
"""

from typing import Dict, List, Set

from src.domain.enums import FactType, RequirementStatus
from src.domain.models import DisputeCase, EvidenceItem, Requirement
from src.domain.rules import RequirementDefinition

# Facts found only on non-primary evidence count for half — they corroborate
# but do not, on their own, establish the requirement.
POOLED_FACT_CREDIT = 0.5


def _fact_types(item: EvidenceItem) -> Set[FactType]:
    return {fact.type for fact in item.extracted_facts}


def evaluate_requirement(
    req_def: RequirementDefinition,
    evidence_items: List[EvidenceItem],
) -> Requirement:
    """Evaluate a single requirement against the evidence set with partial credit."""
    required: Set[FactType] = set(req_def.required_fact_types)

    primary_items = [e for e in evidence_items if e.semantic_type in req_def.required_evidence_types]
    has_primary = len(primary_items) > 0

    primary_facts: Set[FactType] = set().union(*[_fact_types(e) for e in primary_items]) if primary_items else set()
    all_facts: Set[FactType] = set().union(*[_fact_types(e) for e in evidence_items]) if evidence_items else set()

    # Partition required facts into (found on primary), (found only when pooled), (missing).
    covered_primary = required & primary_facts
    covered_pooled = (required & all_facts) - covered_primary
    missing = required - covered_primary - covered_pooled

    if required:
        primary_frac = len(covered_primary) / len(required)
        pooled_frac = len(covered_pooled) / len(required)
        if has_primary:
            coverage = min(1.0, primary_frac + POOLED_FACT_CREDIT * pooled_frac)
        else:
            # No evidence of the right *type*: at best circumstantial.
            coverage = POOLED_FACT_CREDIT * (len(required & all_facts) / len(required))
    else:
        # A requirement with no specific fact demands is met by type presence alone.
        coverage = 1.0 if has_primary else 0.0

    # Status from coverage. SATISFIED demands a primary supporter with full
    # fact coverage; partial coverage is explicitly PARTIALLY_SATISFIED.
    if has_primary and coverage >= 0.999:
        status = RequirementStatus.SATISFIED
    elif coverage > 0.0:
        status = RequirementStatus.PARTIALLY_SATISFIED
    else:
        status = RequirementStatus.MISSING

    # Evidence candidates: primary supporters first, then any item contributing
    # a required fact (so the UI can show what backs a partial requirement).
    primary_ids = [e.id for e in primary_items]
    corroborating_ids = [
        e.id for e in evidence_items
        if e.id not in primary_ids and (_fact_types(e) & required)
    ]

    return Requirement(
        id=req_def.id,
        name=req_def.name,
        description=req_def.description,
        status=status,
        strength=req_def.strength,
        coverage=round(coverage, 4),
        is_auto_win=req_def.is_auto_win,
        evidence_candidates=primary_ids + corroborating_ids,
        satisfied_fact_types=sorted(f.value for f in (covered_primary | covered_pooled)),
        missing_fact_types=sorted(f.value for f in missing),
        source_reference=req_def.source_reference,
    )


def evaluate_requirements(
    case: DisputeCase,
    evidence_items: List[EvidenceItem],
    requirements: List[RequirementDefinition],
) -> List[Requirement]:
    """Evaluate every requirement definition for a case.

    Args:
        case: The dispute case (kept for signature stability / future context).
        evidence_items: The evidence gathered for the case.
        requirements: The network/reason-code requirement definitions.

    Returns:
        One :class:`Requirement` per definition, with coverage and status.
    """
    return [evaluate_requirement(req_def, evidence_items) for req_def in requirements]
