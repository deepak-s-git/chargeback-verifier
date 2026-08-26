# ADR-007: Confidence Thresholds & Gating

## Context
Once evidence is extracted and verified, the system needs to score the overall strength of the dispute response and recommend an action. These scores dictate the workflow state of the dispute.

## Decision
We establish fixed scoring thresholds to gate the dispute workflow:

- **Score ≥ 75 (CONTEST):** The evidence is strong and meets all requirements. Ready for human review and submission.
- **Score 50-74 (REVIEW):** Evidence is moderate or missing minor elements. Requires careful analyst review to decide if it's worth fighting.
- **Score 25-49 (INSUFFICIENT):** Core required evidence is missing. The system recommends accepting the chargeback.
- **Score < 25 (ABSTAIN):** Little to no relevant evidence found.
- **Any Contradiction = MANDATORY REVIEW:** Regardless of the score, if a contradiction is detected (e.g., mismatched billing addresses), the dispute is immediately flagged for mandatory review and cannot be categorized as CONTEST.

### Calibration
Thresholds are calibrated against the validation set of our synthetic benchmark and are *never* tuned against the held-out test set.

## Consequences
- Standardizes the definition of a "strong" vs "weak" case.
- Provides a clear, deterministic gating mechanism based on the combined output of the deterministic rules and AI extraction.

## Amendment (2026-08-26)

The thresholds above are accurate and unchanged. The rebuild specified the **scoring mechanics** underneath them, which this ADR originally left implicit (`src/scoring/scorer.py`):

- **Strength-weighted, not flat-additive.** Each requirement carries a strength weight — REQUIRED = 3, STRONG = 2, SUPPORTING = 1 — and the score is weighted coverage of *satisfied* requirements over a **dynamic per-network denominator** (VISA = 10, MC = 8), so the score tracks the network's real evidence hierarchy.
- **Auto-win floor = 90.** A qualifying Visa CE 3.0 result or a satisfied 3-D Secure requirement lifts the score to a floor of 90 (near-dispositive under network rules).
- **Contradiction penalty = 15**, *and* — as stated above — any contradiction forces the recommendation to REVIEW and the gate to MANDATORY_REVIEW regardless of score (`src/orchestrator/gate.py:58-67`).
- **Injection carries zero numeric penalty** but forces the same REVIEW / MANDATORY_REVIEW routing (`scorer.py:198-199`) — it is a trust signal about the input, not a quality signal about the dispute.

Calibration remains on train/validation only; the test split is run once (see [ADR-009](ADR-009-evaluation-methodology.md)). Full derivation in [docs/rearchitecture-report.md](../rearchitecture-report.md) §5.
