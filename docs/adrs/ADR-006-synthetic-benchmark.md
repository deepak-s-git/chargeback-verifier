# ADR-006: Synthetic Benchmark Design

## Context
To objectively evaluate the system's performance, accuracy, and resilience to edge cases (hallucination, contradiction, injection), we need a rigorous testing methodology. Relying on ad-hoc manual testing is insufficient.

## Decision
We will build a **Synthetic Benchmark** consisting of 200 standardized cases with strict ground truth labels.

### Benchmark Structure:
- **Total Cases:** 200
- **Split:** 60% Train/Dev, 20% Validation, 20% Held-out Test.
- **Case Variations:**
  - **Strong Evidence:** Perfect match for network requirements.
  - **Moderate Evidence:** Meets minimums but lacks compelling extras.
  - **Weak Evidence:** Missing key required fields.
  - **Insufficient Evidence:** Completely misses the mark.
  - **Contradictory Evidence:** E.g., IP address in one doc doesn't match the IP in the system log.
  - **Noisy Evidence:** Embedded in large amounts of irrelevant text.
  - **Adversarial:** Contains prompt injections attempting to bypass AI logic.

### Evaluation Metrics:
- Ground truth labels are defined on a per-requirement, per-case basis.
- Errors are strictly classified by failure type (e.g., False Positive Extraction, Missed Contradiction).

## Consequences
- Provides empirical proof of the system's reliability for the judging panel.
- Allows for automated regression testing as prompts and logic are tuned.

## Amendment (2026-08-26)

The benchmark was rebuilt to make it **coherent by construction**, which is the property the original lacked (the old dataset's labels did not agree with any single rulebook, capping accuracy at 17–23%). The realized design, superseding the generic "Case Variations" above:

- **Generated from the rules the engine implements** (`scripts/generate_dataset.py`), deterministically with `seed=42`, into a fixed **120 / 40 / 40** train / validation / test split (200 cases).
- **Self-validating:** the generator asserts the real engine's verdict matches the intended label as each case is written, so label drift is a hard generation failure.
- **Nine concrete archetypes** (not the loose categories above): `strong_complete`, `strong_ce30`, `strong_3ds` → CONTEST; `moderate_gaps`, `noisy_ocr` → REVIEW; `contradictory`, `adversarial_injection` → REVIEW (forced, regardless of score); `weak_insufficient` → INSUFFICIENT; `insufficient_minimal` → ABSTAIN.
- **Majority-class baseline = 42.5%** (always-CONTEST), the bar any real engine must beat.
- **Honest reading:** a full-engine 100% is an *internal-validity/coherence* result, not out-of-distribution generalization. The substantive signals are the ablation delta, safety-critical recall, the majority baseline, and BEFORE→AFTER.

Methodology and the metric suite are formalized in [ADR-009](ADR-009-evaluation-methodology.md) and [docs/evaluation.md](../evaluation.md).
