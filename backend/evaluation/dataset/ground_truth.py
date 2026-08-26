"""Ground-truth schema for the DisputeShield evaluation dataset.

Each case in the synthetic dataset is paired with a :class:`CaseGroundTruth`
describing what the *system is expected to conclude*. The labels are not
independent human judgements bolted onto arbitrary data — the dataset is
generated coherently (see ``generator.py``): every archetype is constructed so
that the real deterministic engine (``analyze_evidence``) lands in a specific,
pre-computed recommendation band. The evaluation then measures whether the
engine actually agrees, catching mis-calibration, regressions, and detector
gaps.

Fields:

* ``expected_recommendation`` — the target band (CONTEST / REVIEW /
  INSUFFICIENT / ABSTAIN).
* ``expected_score_range`` — inclusive (min, max) score window. For archetypes
  whose recommendation is *forced* by a defensive override (contradictions,
  injection) the numeric score is incidental, so the range is wide.
* ``expected_contradictions`` — how many contradictions the detectors should
  surface (0 for clean cases).
* ``has_injection`` — whether prompt-injection content is present and must be
  flagged.
* ``archetype`` — the generative template (also used to group failures).
* ``network`` — VISA or MASTERCARD (labels are network-invariant by design, but
  the field lets failure analysis spot network-specific breakage).
"""

from typing import Dict, Optional, Tuple

from pydantic import BaseModel, Field


class CaseGroundTruth(BaseModel):
    case_id: str
    expected_recommendation: str  # CONTEST / REVIEW / INSUFFICIENT / ABSTAIN
    expected_score_range: Tuple[int, int]  # inclusive (min, max) on the 0-100 scale
    requirement_labels: Dict[str, str] = Field(default_factory=dict)  # optional: req_id -> status
    expected_contradictions: int = 0  # count of contradictions the detectors should find
    has_injection: bool = False
    archetype: str = ""  # generative template, e.g. "strong_complete"
    network: str = ""  # "VISA" | "MASTERCARD"
    failure_type: Optional[str] = None  # retained for back-compat; mirrors archetype
    notes: str = ""
