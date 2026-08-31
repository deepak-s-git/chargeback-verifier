# Re-architecture Report

**How DisputeShield was rebuilt from a 17–23% prototype into a deterministic, defensible evidence-integrity engine — and how we proved it.**

*Scope: the full BEFORE→AFTER story of the rebuild — what was wrong, what changed, why, and the measured result. Verified 2026-08-26 against the rebuilt engine and the frozen evaluation. Companion documents: [Product](product.md) · [Architecture](architecture.md) · [AI architecture](ai-architecture.md) · [Evaluation](evaluation.md) · [Security](security.md) · [Failure analysis](failure-analysis.md).*

---

## 1. Executive summary

The original prototype ("Chargeback Verifier") scored **17.5–23.3%** recommendation accuracy across its own splits — below its majority-class baseline — while presenting a confident UI full of fabricated numbers. Its dataset was internally incoherent, its scoring was flat and additive, its most safety-critical logic (contradiction detection) was delegated to a non-deterministic LLM, and its persistence layer crashed on any pre-existing database.

We rebuilt it around a single thesis — **AI parses, code decides** — and the result is a system whose entire decision surface is deterministic, reproducible, and auditable. On the held-out test split, recommendation accuracy went from **22.5% → 100%**. That headline number is a *coherence* result, not a generalization claim, and §7 is explicit about what it does and does not prove. The substantive, defensible evidence of quality is elsewhere: a controlled **ablation** shows the deterministic overrides are worth **+17.5 points** on test and are the *only* thing that catches contradictions and injection; the engine beats its **majority-class baseline (42.5%)** decisively; and every claim it emits is grounded to source bytes or blocked.

This document is the honest account of that rebuild.

---

## 2. The BEFORE state

The inherited system had four structural problems, each of which independently undermined trust in its output.

### 2.1 An incoherent dataset
The evaluation dataset had been generated and labeled by processes that did not agree with each other or with any single rulebook. Labels did not correspond to what a correct engine would conclude from the evidence, so *no* engine — however good — could score well against it, and a high score would have been meaningless. Measured accuracy: **Train 23.33% / Validation 17.50% / Test 22.50%** (locked baseline; see [[eval-before-baseline]]).

### 2.2 Flat additive scoring
The scorer summed undifferentiated points per piece of evidence. A mandatory, network-required element counted the same as a nice-to-have supporting document. This produced scores that did not track the network's actual evidence hierarchy, so the resulting recommendations were only incidentally correct.

### 2.3 Non-deterministic safety logic
Contradiction detection — the check that stops a self-contradictory package from being contested — was performed by the LLM. That made the single most consequential safety decision **non-reproducible**: the same evidence could pass one run and fail the next, and there was no way to audit *why* a contradiction was or wasn't found.

### 2.4 A persistence layer that crashed on contact
`CREATE TABLE IF NOT EXISTS` creates a missing table but never alters an existing one. Any database created under an earlier schema kept its old columns forever, and the app crashed with `table cases has no column named dispute_id` the moment it tried to persist a case — which is exactly the path `POST /api/demo/load` takes. The demo did not survive a schema change.

On top of these, the product identity was inconsistent (documentation referred to "Chargeback Verifier (formerly DisputeShield)" — inverting the actual name), the UI displayed fabricated win-probability and fee figures with no backing data, and the docs cited a model version (Gemini 1.5) the code no longer used.

---

## 3. The three binding decisions

Rather than patch these individually, we committed to three decisions that reshaped the whole system.

### Decision 1 — Deterministic-first, LLM-optional
Every load-bearing decision moves into pure deterministic Python. The LLM is confined to **extraction**: reading unstructured evidence into structured facts during ingestion. Everything downstream — requirement evaluation, scoring, gating, contradiction detection, CE 3.0 qualification, claim grounding — is deterministic code with no model in the loop. The system runs **fully without any API key** via a `MockLLMClient` fallback, which also means the evaluation exercises the real decision engine, not a model's mood on a given day. *Rationale and boundary: [AI architecture](ai-architecture.md).*

### Decision 2 — Rebuild the dataset and engine coherently, together
A trustworthy evaluation requires that the rules, the engine, and the labels all mean the same thing. We regenerated the dataset **from the card-network rules themselves** — 9 dispute archetypes, deterministic `seed=42`, 120/40/40 train/validation/test — with a **self-validating generator** that asserts the engine's verdict matches the intended label at generation time. This makes the dataset coherent by construction and makes any future engine/label drift a hard failure rather than a silent accuracy drop. *Methodology and the honest reading of what this proves: [Evaluation](evaluation.md).*

### Decision 3 — Standardize on "DisputeShield"
One name, everywhere, forever. The inverted "formerly DisputeShield" framing is gone; the product is DisputeShield in code, UI, and docs.

---

## 4. What changed, concretely

| Area | BEFORE | AFTER | Where |
|---|---|---|---|
| **Decision locus** | LLM influences verdicts (incl. contradictions) | LLM extracts facts only; all decisions deterministic | `src/orchestrator/analysis.py:76` |
| **Scoring** | Flat additive, evidence-count driven | **Strength-weighted** (REQUIRED:3 / STRONG:2 / SUPPORTING:1), dynamic per-network denominators (VISA=10, MC=8), auto-win floor 90, contradiction penalty 15 | `src/scoring/scorer.py` |
| **Recommendation thresholds** | Ad hoc | CONTEST ≥75, REVIEW ≥50, INSUFFICIENT ≥25, ABSTAIN <25 | `src/scoring/scorer.py` |
| **Contradiction detection** | LLM, non-deterministic | 6 deterministic detectors (IP mismatch, customer-statement conflict, amount mismatch @1% tol, future timestamp, usage-before-purchase, identity mismatch) | `src/verification/contradiction.py` |
| **CE 3.0** | Absent / conflated | Deterministic Visa Compelling Evidence 3.0: 120–365 day window, ≥2 matching elements with ≥1 anchor, ≥2 qualifying prior txns, score floor 90 | `src/verification/ce30.py` |
| **Injection handling** | Unclear | Detected, **zero score penalty**, forces REVIEW + MANDATORY_REVIEW (flag-and-route, never mutate) | `src/security/injection.py`, `src/orchestrator/gate.py:58-67` |
| **Claim integrity** | LLM prose | Templated claims, grounded to `sha256(raw_content)` + presence, else BLOCKED | `src/verification/claim_verifier.py:40` |
| **Package** | Fabricated metrics | Verified-claims-only draft, `action="draft"` hard invariant | `src/packaging/razorpay_mapper.py:60` |
| **Persistence** | Crashed on old schema | Idempotent `_reconcile_columns` self-heal + env-configurable DB path | `src/database/migrations.py:52`, `src/database/db.py:31` |
| **Frontend** | Fabricated win-prob / fees | Real data only across a 7-tab workbench; fabricated metrics removed | `src/features/case/CaseWorkspace.tsx` |
| **Verification** | Manual/none | In-process `TestClient` contract check (full ASGI stack, no socket bind) | `backend/scripts/contract_check.py` |

---

## 5. The scoring rewrite in detail

The single most important engine change is the move from additive to **strength-weighted** scoring, because it is what makes the recommendation track the network's real evidence hierarchy.

- Each requirement carries a strength (`REQUIRED`, `STRONG`, `SUPPORTING`) with weights **3 / 2 / 1**.
- The score is the weighted coverage of *satisfied* requirements over a **dynamic denominator** computed from the network's own requirement set — **10 for Visa, 8 for Mastercard** — not a fixed constant. This is why a Mastercard case and a Visa case are scored on their own scales rather than a one-size-fits-all total.
- **Auto-win floors:** a qualifying CE 3.0 result or a satisfied 3-D Secure requirement lifts the score to a floor of **90**, reflecting that these are near-dispositive under network rules.
- **Contradictions** apply a fixed penalty (15) *and*, more importantly, force the recommendation down to REVIEW and the gate to MANDATORY_REVIEW regardless of score — a strong-but-contradicted case is exactly the one a human must see.
- **Injection** applies **no numeric penalty at all** — it is not a quality signal about the dispute, it is a trust signal about the input — but it forces the same human-review routing.

The thresholds (CONTEST ≥75 / REVIEW ≥50 / INSUFFICIENT ≥25 / ABSTAIN <25) then map score to recommendation. Because the denominators and weights are derived from the rules the dataset was generated from, the scorer and the labels are two views of the same rulebook — which is the whole point of Decision 2.

---

## 6. How we verified it (without a browser or a socket)

The sandbox blocks socket binds and outbound localhost, so a live dev-server smoke test was impossible. Rather than declare the system working because it *looked* done, we built an **in-process contract check** (`backend/scripts/contract_check.py`) using `fastapi.testclient.TestClient`, which drives the complete ASGI application — routing, dependency injection, DB, pipeline — with no network. It exercises the real request/response contract end to end (create case → upload → analyze → package → audit) against the actual schemas.

This caught the migration crash as a reproducible failure and now guards against its return via a dedicated regression suite (`backend/tests/unit/test_migrations.py`) that builds an *old, populated* table, runs `init_db`, and asserts the missing columns appear with the legacy row intact. Full suite: **26 passed**.

The principle: **do not declare success because the app runs.** Success is a passing contract check, a green regression suite, and an evaluation that reproduces deterministically — all three.

---

## 7. Results — and exactly what they mean

### 7.1 The numbers

| Metric (held-out **test** split, n=40) | BEFORE | AFTER (full engine) | AFTER (ablation) |
|---|---|---|---|
| Recommendation accuracy | 22.5% | **100%** | 82.5% |
| Macro-F1 | — | 100% | 88.3% |
| Score-in-range | — | 40/40 | 35/40 |
| Contradiction recall | — | 4/4 (100%) | **0/4 (0%)** |
| `strong_ce30` archetype | — | 5/5 | **0/5** |
| Majority-class baseline | — | 42.5% | 42.5% |

Validation and train reproduce the same pattern (full: 100% / 100%; ablation: 95% / 80%). The test split was **run exactly once**, on 2026-08-26, after all calibration was frozen; determinism was confirmed by re-running validation first and reproducing its numbers exactly. See [[eval-after-results]].

### 7.2 What 100% is — and is not

**It is not a generalization claim.** The dataset labels were hand-derived from card-network rules, and the generator asserts the engine agrees with them. So 100% proves that **rules ⟺ engine ⟺ labels are mutually consistent**, that there is no calibration drift, and that the result is **deterministic on samples not used for calibration**. It does **not** prove the engine would score 100% on real-world merchant disputes drawn from a different distribution — both sides of this evaluation share the same generative distribution. We state this plainly because a system whose thesis is "never overstate what the evidence supports" must hold its own metrics to that bar.

### 7.3 What the substantive signals are

The defensible evidence of quality is not the 100% — it is:

1. **The ablation delta.** Turning off the deterministic overrides (CE 3.0, contradiction, injection) drops test accuracy by **17.5 points** and makes the engine miss **every** contradiction and **every** injection, with the `strong_ce30` archetype collapsing to 0/5. This isolates the value of the deterministic core: it is not decoration, it is the safety-critical machinery.
2. **The majority baseline.** Always-guess-CONTEST scores 42.5% on test; the engine clears that by a wide, meaningful margin.
3. **BEFORE→AFTER on the same held-out split.** 22.5% → 100% on data neither engine calibrated against.
4. **Safety-critical recall.** The full engine catches 4/4 contradictions and (on the splits containing them) injection attempts; the ablation catches none. For a defense-only system, missing a contradiction is the expensive error, and the deterministic core is what prevents it.

Score-in-range is partly definitional (it uses the same scoring formula), so we lean on band accuracy and the ablation as the substantive claims rather than on score-in-range.

---

## 8. What we deliberately did not fix (yet)

Honesty requires naming the deferred work rather than implying completeness. The [Security](security.md) register and [Failure analysis](failure-analysis.md) carry the full lists; the headline deferrals are:

- **No authentication/authorization** — every route is open (IDOR). Accepted, documented prototype risk; there is no login UI by design.
- **PII plaintext at rest** and served to unauthenticated callers.
- **The injection denylist is coarse and evadable** — it is a tripwire feeding the human gate, not a barrier, and the substantive defense remains the deterministic core + mandatory review.
- **Grounding is substring-presence, not semantic** — it verifies a fact's value appears in its source bytes, not that the fact is contextually relevant.
- **`deep_dive.md` is stale** — it predates the rebuild (wrong name framing, Gemini 1.5, additive scoring, the old baseline narrative) and needs regeneration; the current docs supersede it.

Each non-breaking hardening item is queued to land with a regression test and a full `pytest` + contract-check + evaluation re-run to prove no behavioral drift.

---

## 9. The lesson

The rebuild's core move was to **stop asking the model to be trustworthy and instead make the system trustworthy without it.** The LLM is genuinely useful — reading a garbled CSV or a PDF into clean facts is exactly what it is good at — but it is the wrong place for a decision that must be reproducible, auditable, and safe. By pushing every consequential judgment into deterministic code and grounding every claim in source bytes, DisputeShield became a system you can *check*, not just one you can run. The evaluation, the ablation, and the contract tests are how we check it — and why the 100% is presented with its caveats rather than as a trophy.

---

*Next: [Evaluation](evaluation.md) for the full methodology and metric definitions; [Architecture](architecture.md) for the system structure that realizes these decisions.*
