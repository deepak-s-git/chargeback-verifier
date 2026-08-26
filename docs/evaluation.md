# Evaluation

**DisputeShield — how the decision engine is measured, what the numbers are, and exactly what they prove.**

*Scope: the evaluation methodology, dataset design, metric suite, the BEFORE→AFTER and ablation results, and an honest reading of their meaning. Verified 2026-08-26 against the frozen engine and dataset. Companion documents: [Re-architecture report](rearchitecture-report.md) · [Failure analysis](failure-analysis.md) · [AI architecture](ai-architecture.md) · [Architecture](architecture.md).*

---

## 1. What is being evaluated (and what is not)

The evaluation measures the **deterministic decision engine** — `analyze_evidence` (`src/orchestrator/analysis.py:76`) — over structured facts, under the deterministic `MockLLMClient`. It answers: *given the extracted facts for a case, does the engine produce the recommendation, score band, and safety flags that the card-network rules require?*

It does **not** measure the LLM extraction step. Extraction fidelity — whether the model correctly reads facts out of a messy PDF — is a separate, currently-unmeasured surface (see [Failure analysis](failure-analysis.md) §8). Keeping the two apart is deliberate: the decision engine is the part that must be reproducible and auditable, so it is the part with a rigorous, deterministic evaluation.

---

## 2. The methodology, and why it is trustworthy

A prior version of this system scored 17–23% because its dataset, engine, and labels did not agree with one another (see [Re-architecture report](rearchitecture-report.md) §2). The rebuild fixes this at the root with three methodological commitments:

1. **Coherent generation from the rules.** The dataset is generated *from the same card-network rules the engine implements* (`scripts/generate_dataset.py`), deterministically with `seed=42`, into a fixed 120 / 40 / 40 train / validation / test split (200 cases total).
2. **Self-validation at generation time.** Each case is built to a target recommendation band, and the generator asserts the real engine agrees with the intended label as it writes the case. Label drift becomes a hard generation failure, not a silent accuracy loss.
3. **Held-out test discipline.** The `test` split is run **once, at the very end**, after all calibration is frozen; a loud banner prints whenever it is touched (`evaluate.py:62-65`). All iteration happens on train/validation.

These make the evaluation *internally valid by construction*. §7 is explicit about the ceiling this creates: internal validity is not the same as generalization.

---

## 3. The dataset: nine archetypes

Each case belongs to one of nine archetypes, each engineered to a **network-invariant recommendation band** under the real scorer (weights REQUIRED=3 / STRONG=2 / SUPPORTING=1; VISA denominator 10, MC 8; auto-win floor 90; thresholds CONTEST ≥75 / REVIEW ≥50 / INSUFFICIENT ≥25 / ABSTAIN <25). See [[dataset-archetype-scores]] for the exact per-network point derivations.

| Archetype | Target | What it exercises | Count (of 200) |
|---|---|---|---|
| `strong_complete` | CONTEST | Full requirement coverage | 50 |
| `strong_ce30` | CONTEST | Visa Compelling Evidence 3.0 auto-win (forces VISA) | 20 |
| `strong_3ds` | CONTEST | 3-D Secure auto-win (ECI/CAVV/DS_TRANS_ID) | 15 |
| `moderate_gaps` | REVIEW | Partial coverage, borderline score | 35 |
| `weak_insufficient` | INSUFFICIENT | Some support, below the bar | 30 |
| `insufficient_minimal` | ABSTAIN | Almost nothing to stand on | 15 |
| `contradictory` | REVIEW (forced) | IP mismatch + customer-statement conflict | 20 |
| `noisy_ocr` | REVIEW | `moderate_gaps` + cosmetic noise (values kept intact) | 10 |
| `adversarial_injection` | REVIEW (forced) | Injection phrases in evidence | 5 |

**Label distribution:** CONTEST 85, REVIEW 70, INSUFFICIENT 30, ABSTAIN 15. The **majority-class baseline** (always guess CONTEST) is therefore **42.5%** — the number any real engine must beat to be worth anything.

Two archetypes test the **safety-critical** path specifically: `contradictory` and `adversarial_injection` are labeled REVIEW *regardless of score*, because catching them is more important than any score. The 5 injection cases all fall in the train split (so test/validation report injection as n/a — nothing to detect).

---

## 4. The metric suite

Computed by `backend/evaluation/metrics.py`; the machine-readable report JSON has top-level keys `{split, mode, metrics, failures, predictions}`, with `metrics` containing:

| Key | Meaning |
|---|---|
| `accuracy` | Recommendation accuracy — the headline correctness metric |
| `macro_precision` / `macro_recall` / `macro_f1` | Per-class averaged, so minority classes count equally |
| `weighted_f1` | Support-weighted F1 |
| `per_class` / `support` | Precision/recall/F1 and case count per recommendation |
| `confusion` | Full confusion matrix over the four recommendations |
| `majority_class` / `majority_baseline` | The trivial baseline (CONTEST, 42.5%) |
| `score_in_range` | Fraction of cases whose numeric score lands in the archetype's expected band |
| `contradiction` | Precision/recall/F1 + exact-count accuracy for contradiction detection |
| `injection` | The same for injection detection (n/a where a split has no positives) |
| `total` | Case count |

`failures` is a per-archetype and confusion-pair breakdown; `predictions` is the full per-case record for audit. We report **recommendation accuracy** and **macro-F1** as the primary correctness metrics, and **contradiction/injection recall** as the safety metrics — deliberately not leaning on `score_in_range`, which is partly definitional (it uses the same scoring formula the labels were derived from).

---

## 5. Results

### 5.1 BEFORE → AFTER (recommendation accuracy)

| Split | BEFORE (old engine, old data) | AFTER — full engine | AFTER — partial ablation |
|---|---|---|---|
| Train (120) | 23.33% | **100%** | 80.0% |
| Validation (40) | 17.50% | **100%** | 95.0% |
| **Test (40, held out)** | **22.50%** | **100%** | 82.5% |
| Majority baseline | 42.5% | 42.5% | 42.5% |

The full engine reproduces **100%** on all three splits; the test split was run exactly once, on 2026-08-26, with determinism confirmed by first reproducing validation's numbers. The locked BEFORE numbers are recorded in [[eval-before-baseline]]; the AFTER numbers in [[eval-after-results]].

### 5.2 The ablation (this is the substantive result)

The `partial` mode disables the deterministic overrides — CE 3.0 qualification, contradiction detection, and injection routing — leaving requirements + scoring only. It isolates what those overrides are worth:

| Signal (test split) | Full | Partial | Delta |
|---|---|---|---|
| Recommendation accuracy | 100% | 82.5% | **−17.5 pts** |
| Macro-F1 | 100% | 88.3% | −11.7 pts |
| Contradiction recall | 4/4 (100%) | **0/4 (0%)** | catches none |
| `strong_ce30` archetype | 5/5 | **0/5** | collapses |
| Score-in-range | 40/40 | 35/40 | −5 |

Turning off the overrides makes the engine miss **every** contradiction and **every** injection, and the CE 3.0 archetype collapses entirely. For a defense-only system, missing a contradiction is the expensive error — so this table, not the 100%, is the real evidence that the deterministic core earns its place.

---

## 6. How to reproduce

From the repository root, using the backend virtualenv:

```bash
backend/venv/bin/python scripts/run_evaluation.py --split validation --mode full
```

- `--split` ∈ `train | validation | test`; `--mode` ∈ `full | partial`.
- The runner sets its own import paths, so no `PYTHONPATH` prefix is needed.
- Reports are written to `backend/evaluation/reports/` as `evaluation_report_{split}_{mode}.{txt,json}`. That directory is **git-ignored**: the reports are deterministic, regenerable artifacts, and *this document* is the committed record of the numbers.
- To regenerate the dataset itself: `backend/venv/bin/python scripts/generate_dataset.py` (deterministic, `seed=42`).
- **Do not run `--split test` to iterate.** It is the held-out final measurement; the banner exists to keep it that way.

---

## 7. What the 100% means — and what it does not

This section is the most important in the document, because the headline number is the easiest thing to misread.

**What 100% proves:** the card-network **rules**, the **engine** that implements them, and the dataset **labels** are mutually consistent; there is no calibration drift; and the result is **deterministic on samples never used for calibration** (the held-out test split reproduces exactly). This is a strong *internal-validity* result — the system is coherent and reproducible end to end.

**What 100% does not prove:** generalization to real-world merchant disputes. Both sides of the evaluation are drawn from the **same generative distribution**; the labels were hand-derived from the same rules the engine encodes. A perfect score here does **not** imply a perfect score on messy, out-of-distribution production evidence — and claiming otherwise would be exactly the overclaiming this product exists to prevent.

**Therefore the substantive, defensible claims are:**
1. **The ablation delta** — the deterministic overrides are worth +17.5 points on the held-out test and are the *only* thing catching contradictions and injection (§5.2).
2. **Safety-critical recall** — 4/4 contradictions caught by the full engine; 0/4 by the ablation.
3. **The majority baseline** — 42.5%, cleared decisively.
4. **BEFORE→AFTER on the same held-out split** — 22.5% → 100%.

Score-in-range is reported for completeness but treated as partly definitional; the weight of the argument rests on band accuracy plus the ablation.

---

## 8. Known evaluation gaps

- **Extraction is not evaluated.** The suite runs on structured facts under the mock client; real LLM extraction errors are unmeasured (see [Failure analysis](failure-analysis.md) §8). A separate extraction-fidelity evaluation is the right next step.
- **`noisy_ocr` tests decision robustness, not extraction recovery** — it adds cosmetic noise but keeps fact values groundable ([[dataset-archetype-scores]]).
- **Single generative distribution** — as in §7, there is no independent, human-labeled, out-of-distribution test set. Building one is the highest-value evaluation investment beyond this work.

---

*The evaluation is the reason the [Re-architecture report](rearchitecture-report.md)'s claims can be trusted, and the [Failure analysis](failure-analysis.md) is where its limits are turned into a work list. The honesty of §7 is not a hedge — it is the same standard the product applies to every claim it makes about a merchant's evidence.*
