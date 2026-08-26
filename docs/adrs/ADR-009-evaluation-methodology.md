# ADR-009: Evaluation Methodology

> **Status:** Accepted 2026-08-26. Supersedes the generation approach in [ADR-006](ADR-006-synthetic-benchmark.md); formalizes the scoring calibration in [ADR-007](ADR-007-confidence-threshold.md).

## Context

The original synthetic benchmark ([ADR-006](ADR-006-synthetic-benchmark.md)) had a fatal flaw discovered during the rebuild: its ground-truth labels did not agree with any single, implementable rulebook. Cases labeled CONTEST contained evidence the rules score as INSUFFICIENT, and vice versa. No correct engine could have scored well against it — the ceiling was **17–23% accuracy**, and that ceiling was a property of the *dataset*, not the engine. An evaluation that a correct system cannot pass is worse than no evaluation, because it produces false signal.

We needed a methodology where the labels are correct by construction, the split discipline is honest, and the headline metric is interpreted without overstatement.

## Decision

We rebuild the benchmark to be **coherent by construction** and evaluate against it with an explicit, reproducible protocol.

1. **Generate from the rules the engine implements.** `scripts/generate_dataset.py` synthesizes cases deterministically (`seed=42`) into a fixed **120 / 40 / 40** train / validation / test split (200 cases total).
2. **Self-validate at generation time.** As each case is written, the generator runs the real engine and asserts the verdict matches the intended label. Label drift is a hard generation failure, not a silent inconsistency.
3. **Nine named archetypes** span the decision space: `strong_complete`, `strong_ce30`, `strong_3ds` → CONTEST; `moderate_gaps`, `noisy_ocr` → REVIEW; `contradictory`, `adversarial_injection` → REVIEW (forced regardless of score); `weak_insufficient` → INSUFFICIENT; `insufficient_minimal` → ABSTAIN.
4. **Held-out test discipline.** Thresholds and logic are calibrated on train/validation only. The test split is run **once**; its numbers are the reported result and are never used to tune.
5. **Ablation as the real signal.** Every split is run in `full` mode (whole engine) and `partial` mode (safety layers ablated) so the delta attributable to the deterministic safety machinery is measurable, not asserted.
6. **A full metric suite, not just accuracy:** per-class precision/recall/F1, macro/weighted F1, confusion matrix, the majority-class baseline (**42.5%**, always-CONTEST), score-in-range, and dedicated contradiction/injection recall (`backend/evaluation/evaluate.py`).

## Consequences

- **A full-engine 100% is an internal-validity / coherence result, not out-of-distribution generalization.** We say this plainly wherever the number appears. The dataset proves the engine is self-consistent with its own rulebook; it does not prove performance on real merchant evidence.
- **The substantive signals are the honest ones:** the ablation delta (+17.5 points, full vs partial on test), safety-critical recall (injection/contradiction routed 4/4 vs 0/4 ablated), the 42.5% majority baseline the engine must beat, and the BEFORE→AFTER jump from the incoherent-dataset ceiling.
- **Extraction is not tested.** The evaluation exercises the decision core over pre-structured facts; it does not measure LLM extraction quality (candidly flagged in [failure-analysis.md](../failure-analysis.md) §8). This is the most important limitation of the number.
- **Reproducible by anyone, with no API key:** `backend/venv/bin/python scripts/run_evaluation.py --split validation --mode full`. Reports write to `backend/evaluation/reports/` (git-ignored); the committed record of results lives in [docs/evaluation.md](../evaluation.md).
- Full methodology, tables, and the "what 100% means / does not mean" section are in [docs/evaluation.md](../evaluation.md); scoring mechanics in [ADR-007](ADR-007-confidence-threshold.md) and [docs/rearchitecture-report.md](../rearchitecture-report.md) §5.
