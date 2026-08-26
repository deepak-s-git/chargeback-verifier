# Failure Analysis

**DisputeShield — where the engine can still be wrong, and how it fails when it does.**

*Scope: the honest limits of the decision engine, the grounding layer, and the evaluation itself — independent of the deployment-security gaps in [Security](security.md)/[Threat model](threat-model.md). Verified 2026-08-26 against `backend/src`. Companion documents: [Evaluation](evaluation.md) · [AI architecture](ai-architecture.md) · [Re-architecture report](rearchitecture-report.md).*

---

## 1. How the system is designed to fail

Before cataloguing weaknesses, the intended failure posture: DisputeShield is **defense-only** and biased toward **human review**. The expensive errors for this product are (a) recommending CONTEST on a case that is actually contradicted or insufficient — *overclaiming* — and (b) failing to notice a contradiction or an injection attempt. The gate is built so that **any** contradiction, **any** injection flag, or **any** ungroundable claim pulls the case to `REVIEW`/`MANDATORY_REVIEW` regardless of score (`src/orchestrator/gate.py:58-67`, `src/scoring/scorer.py:198-199`). So when the system's inputs are within the patterns it understands, it fails *safe* — toward a human — rather than toward a wrong autonomous action (which it cannot take at all; `action="draft"`).

The failures that matter, then, are the ones where the system is **silently confident and wrong** — where a real problem falls outside the patterns the deterministic core recognizes, so nothing trips the gate. Those are catalogued below.

---

## 2. Grounding is presence, not meaning

**The limitation.** `verify_claim` (`src/verification/claim_verifier.py:40`) grounds a claim with two checks (`:26-37`): integrity — `fact.provenance.content_hash == sha256(evidence.raw_content)` — and presence — the fact's value appears (case-insensitive **substring**) in that source text. A claim VERIFIES if *any one* cited evidence item grounds *any* fact (`:58-69`).

**How it fails.**
- **Trivial grounding of short/common values.** An `AMOUNT` fact `"100"` grounds against any `"100"` substring in a log line unrelated to payment; a `CURRENCY` `"INR"` grounds against any mention of INR. Presence is satisfied without the fact being *about* what the claim asserts.
- **Any-fact/any-evidence matching.** The relevant fact for a requirement need not be the one that grounds; a claim can verify on an incidental match while its load-bearing fact is unverified.

**Blast radius.** Bounded by the fact that claims are only minted for requirements the deterministic engine already marked SATISFIED, and package content is verified-claims-only — so this inflates confidence in a claim that the requirement engine already accepted; it does not manufacture a new claim from nothing. But it means "VERIFIED" is weaker than it sounds.

**Detection / fix.** Minimum-specificity rules per fact type (reject grounding on values below a length/entropy threshold) and requirement-to-fact binding so the *relevant* fact must ground. Tracked as [Security](security.md) §7 #9.

---

## 3. Contradiction detection is pattern-specific, and severity is unused

**The limitation.** Six deterministic detectors run (`src/verification/contradiction.py`): IP mismatch, customer-statement conflict, amount mismatch (1% tolerance), future timestamp, usage-before-purchase, identity mismatch. Two facts about the system:

1. **Coverage is exactly those six patterns.** A contradiction that is real but not one of these shapes (e.g. a delivery-address conflict, a product-category mismatch, a currency conflict) is **not detected** and will not trip the gate.
2. **`Contradiction.severity` is computed but never consumed.** The gate treats *any* contradiction identically — a 1%-boundary amount mismatch routes exactly like a flat customer denial. This is deliberately conservative (all contradictions → review) but coarse: it cannot prioritize, and it cannot distinguish a fatal contradiction from a cosmetic one for the analyst.

**How it fails.** A case with a genuine but out-of-pattern contradiction can score high and recommend CONTEST with nothing flagged — the silent-and-wrong failure mode. Within-pattern, the amount detector's 1% tolerance is a hard edge: a 1.0%-vs-1.01% discrepancy flips detection.

**Detection / fix.** Treat the detector set as extensible and add detectors as new contradiction shapes are observed; if severity is to remain, either consume it in gating/prioritization or remove it to avoid implying a gradation the gate does not act on (mirrors the dead-code honesty principle in [Security](security.md) §7 #3).

---

## 4. CE 3.0 qualification is binary, with hard edges

**The limitation.** Visa Compelling Evidence 3.0 (`src/verification/ce30.py`) qualifies only when **all** of: transactions fall in the **120–365 day** window (inclusive), there are **≥2 matching elements including ≥1 anchor** (IP / DeviceID / DeviceFingerprint), and **≥2 qualifying prior transactions**. Qualification lifts the score to a floor of 90; non-qualification contributes nothing extra.

**How it fails.** There is **no partial CE 3.0 credit**. A case with two strong matching elements but only one qualifying transaction, or a transaction at day 119, or two matching elements where none is an anchor, fails qualification *entirely* and loses the entire CE 3.0 lift. For a genuinely strong-but-boundary case this is a false negative — the engine will under-credit it. This is the correct conservative reading of the network rule (the rule itself is binary), but it means borderline legitimate CE 3.0 cases land in REVIEW/INSUFFICIENT rather than CONTEST. The ablation makes the dependency vivid: with CE 3.0 disabled, the `strong_ce30` archetype collapses from 5/5 to **0/5** ([Evaluation](evaluation.md)).

**Detection / fix.** Surface *why* CE 3.0 failed (which constraint missed) to the analyst so a boundary miss is visible rather than silent; consider a "near-miss CE 3.0" advisory that still routes to review.

---

## 5. Timeline anomaly coverage is narrow

**The limitation.** `build_timeline` emits only `FUTURE_TIMESTAMP` and `DUPLICATE_EVENT` anomalies (`src/verification/timeline_builder.py:92-111`). Three defined anomaly types — `IMPOSSIBLE_ORDER`, `SUSPICIOUS_GAP`, `MISSING_EXPECTED_EVENT` — are **never produced** (see [Domain model](domain-model.md) on intentionally-unused enum values).

**How it fails.** Temporal problems outside those two shapes are not surfaced *as timeline anomalies*. In practice the most dangerous ordering problem — usage before purchase — is caught by the contradiction layer instead (§3), so this is partly redundancy rather than a pure gap; but "suspicious gap" and "missing expected event" have no coverage anywhere.

**Detection / fix.** Either implement the defined anomaly types or document them as reserved; the current state is honest but the enum implies more than the builder delivers.

---

## 6. The requirement model has no "contradicted" state

**The limitation.** The requirement engine emits only `SATISFIED`, `PARTIALLY_SATISFIED`, and `MISSING` (`src/verification/requirement_engine.py:71-76`); `RequirementStatus.CONTRADICTED` and `NOT_APPLICABLE` are defined but never used. Contradictions are modeled **separately** and gate the whole case rather than marking a specific requirement as contradicted.

**How it fails.** This is a modeling simplification, not a correctness bug — but it means the UI cannot show "this requirement is satisfied *but contradicted*"; it shows the requirement as satisfied and the contradiction as a case-level flag. An analyst must connect the two mentally. For a case where a satisfied requirement is precisely the thing being contradicted, the coupling is implicit.

**Detection / fix.** Bind contradictions to the requirement(s) they undermine and surface `CONTRADICTED` at the requirement level.

---

## 7. The base scorer alone is not safe — the overrides are the safety net

**The limitation.** The strength-weighted scorer produces a number; the *safety* comes from the deterministic overrides layered on top (CE 3.0 floor, contradiction penalty + forced review, injection forced review). The ablation quantifies this: strip the overrides and contradiction recall and injection recall both drop to **0%**, and test accuracy falls 17.5 points ([Evaluation](evaluation.md)).

**How it fails.** This is by design — but it means the correctness of the whole system rests on the overrides being both *correct* and *complete*. Any gap in §3 (contradiction coverage) or §2 (grounding) is a gap in the safety net, not just the score. The scorer will happily rate a contradicted-but-out-of-pattern case at CONTEST because the override that would have caught it never fired.

**Detection / fix.** This is the reason §3's detector set must be treated as living, and the reason the evaluation leans on **ablation and safety-critical recall** rather than the headline accuracy.

---

## 8. The evaluation does not test extraction

**The most important blind spot.** The evaluation exercises `analyze_evidence` on **structured facts**, with the deterministic `MockLLMClient` — it measures the **decision engine**, not the **LLM extraction** step that produces those facts in real use. Therefore:

- Real-world extraction failures — a missed fact in a garbled PDF, a misclassified evidence type, an OCR-style corruption that survives parsing — are **not measured** by any current metric.
- The `noisy_ocr` archetype adds cosmetic noise but **keeps fact values intact so they still ground** (see [[dataset-archetype-scores]]); it tests robustness of the decision to noise, not the extractor's ability to recover facts from genuinely degraded input.

**How it fails.** A case can be decided perfectly *given correct facts* while the facts themselves are wrong because extraction erred — and the evaluation would not catch it. Garbage-in still yields confident-out here, and that path is untested.

**Detection / fix.** A separate extraction-fidelity evaluation (known documents → expected facts, scored on extraction precision/recall) against the real LLM client, kept distinct from the decision evaluation. Documented as a known gap in [Evaluation](evaluation.md).

---

## 9. 100% is coherence, not generalization

Restated here because it is a failure-analysis fact, not just an evaluation caveat: the full-engine 100% (including on the held-out test split) proves **rules ⟺ engine ⟺ labels** are mutually consistent and deterministic on non-calibration samples. It does **not** prove generalization to real-world disputes drawn from a different distribution — both sides of the evaluation share one generative distribution. Treating the 100% as a generalization claim would itself be the overclaiming the product exists to prevent. The substantive signals are the **ablation delta**, **safety-critical recall**, the **majority baseline (42.5%)**, and **BEFORE→AFTER (22.5%→100%)**. See [Evaluation](evaluation.md) §on interpretation.

---

## 10. Product/UX failure surfaces

Not decision errors, but real gaps that affect whether the analyst is served (see [UX](ux.md)):

- **No upload UI is wired.** Three API client functions (`analyzeCase`, `getTimeline`, `uploadEvidence`) are exported but unused; the modal copy references adding evidence from the Evidence tab, but no upload control is connected. Evidence enters via the demo loader / API only.
- **Desktop-only.** No responsive breakpoints; unusable on small viewports.
- **Modal accessibility gaps.** No focus trap, no `role="tab"` semantics, no Escape-to-close.

**Disposition.** Documented, not hidden; the workbench is a faithful *read* surface over real data (no fabricated metrics), with the *write* path (upload) not yet built in the UI.

---

## 11. Failure disposition summary

| # | Failure mode | Fails safe? | Disposition |
|---|---|---|---|
| 2 | Substring grounding | Inflates confidence within an already-satisfied req | Documented; specificity rules planned |
| 3 | Out-of-pattern contradiction | **No — silent** | Detector set must stay living; highest engine-correctness concern |
| 3 | Severity computed, unused | Yes (all → review) | Consume or remove |
| 4 | Binary CE 3.0, hard edges | Yes (under-credits) | Surface failure reason |
| 5 | Narrow timeline anomalies | Partly (contradictions overlap) | Implement or reserve |
| 6 | No requirement-level CONTRADICTED | Yes (case-level flag) | Bind contradictions to requirements |
| 7 | Overrides are the safety net | Yes if overrides complete | Rely on ablation + recall metrics |
| 8 | Extraction untested in eval | **No — unmeasured** | Separate extraction-fidelity eval |
| 10 | No upload UI, desktop-only, a11y | N/A (UX) | Documented |

The two entries that do **not** fail safe — out-of-pattern contradictions (§3) and untested extraction (§8) — are the ones to watch. Both are inherent to the current design's scope, both are documented rather than hidden, and both have a concrete detection/fix path.

---

*A system whose thesis is "never overstate what the evidence supports" must apply that standard to itself. This document is that self-application. See [Evaluation](evaluation.md) for the measurements behind these claims and [Re-architecture report](rearchitecture-report.md) for how the design got here.*
