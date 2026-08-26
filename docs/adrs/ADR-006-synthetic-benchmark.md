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
