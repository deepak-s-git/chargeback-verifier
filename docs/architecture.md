# Architecture

**DisputeShield — a hybrid system where the LLM parses and deterministic code decides.**

*Scope: the system's structure, its three-phase pipeline, module layout, and persistence. Verified 2026-08-26 against `backend/src`. This document supersedes the pre-rebuild architecture notes. Companion documents: [AI architecture](ai-architecture.md) · [Domain model](domain-model.md) · [Security](security.md) · [Evaluation](evaluation.md).*

---

## 1. The shape of the system

DisputeShield is a FastAPI backend and a React workbench over a SQLite store. Its defining architectural property is a **hard boundary between parsing and deciding**:

- The **LLM layer** (or a deterministic mock) runs exactly once per evidence item, at upload, to *propose* structured facts from unstructured content.
- Every **decision** — which requirements are satisfied, the score, the recommendation, the review gate, contradictions, CE 3.0 qualification, claim grounding — is **pure deterministic Python** with no model in the loop.

This is not a stylistic preference; it is what makes the system's output reproducible and auditable, and it is validated by the evaluation (see [Evaluation](evaluation.md)). The rest of this document traces how requests move through that structure.

---

## 2. The three-phase pipeline

A common misreading is that "analysis" is one monolithic step. It is not. Work is split across **three distinct `CaseService` methods**, invoked at different times by different routes, with different trust and cost profiles:

```
  Phase 1 — INGEST + EXTRACT            Phase 2 — DECIDE                 Phase 3 — PACKAGE
  (CaseService.add_evidence,            (analyze_evidence,               (CaseService.generate_package
   at upload time)                       src/orchestrator/analysis.py:76)  → razorpay_mapper)
  ┌───────────────────────────┐        ┌───────────────────────────┐    ┌──────────────────────────┐
  │ validate_file             │        │ get_requirements          │    │ collect VERIFIED claims  │
  │ detect_injection (upload) │        │ build_timeline            │    │ assemble explanation     │
  │ parse (csv/json/txt/pdf)  │        │ evaluate_requirements     │    │   letter w/ [EV-…] cites │
  │ classify evidence type    │        │ evaluate_ce30 (VISA only) │    │ shape network payload    │
  │ EXTRACT facts (LLM/mock)  │        │ detect_contradictions     │    │ action = "draft"  ◄─hard │
  │ persist to SQLite         │        │ detect_injection (union)  │    │   invariant, never submit│
  └───────────────────────────┘        │ score_evidence            │    └──────────────────────────┘
         ▲                              │ mint+verify claims        │
         │ POST /cases/{id}/evidence    │   (SATISFIED reqs only)   │           ▲
         │                              │ apply_gate                │           │ GET /cases/{id}/package
         │                              └───────────────────────────┘           │
         │                                     ▲
         │                                     │ POST /cases/{id}/analyze
         │                                     │ GET  /cases/{id}/analysis (re-runs)
   merchant evidence                     (no LLM, no IO — pure function of stored facts)
```

**Why the split matters:**

- **Phase 1 is the only place untrusted input meets the model**, and the only place with IO cost. Injection is checked here first; evidence is parsed and classified; facts are extracted and persisted. After this phase, everything downstream operates on stored, structured facts.
- **Phase 2 is a pure function.** `analyze_evidence(case, evidence_items)` (`src/orchestrator/analysis.py:76`) performs verification → scoring → gating and nothing else — no LLM call, no file IO, no network. Given the same stored facts it always produces the same result, which is exactly why the evaluation can treat it as the deterministic system under test. Its docstring notes explicitly that extraction already happened during ingestion (`analysis.py:12-15`).
- **Phase 3 compiles, it does not act.** Packaging assembles a draft from verified claims only and hardcodes `action="draft"` (`src/packaging/razorpay_mapper.py:60`). There is no submit path anywhere in the codebase.

### 2.1 Phase 2, step by step

The decision phase runs in a fixed order (`analysis.py:76` onward):

1. **`get_requirements`** — load the requirement set for the case's network + reason code from the rules module.
2. **`build_timeline`** — order evidence events, flagging `FUTURE_TIMESTAMP` and `DUPLICATE_EVENT` anomalies.
3. **`evaluate_requirements`** — for each requirement, determine SATISFIED / PARTIALLY_SATISFIED / MISSING from grounded fact types and compute coverage.
4. **`evaluate_ce30`** — Visa only; test Compelling Evidence 3.0 qualification (date window, matching elements + anchor, qualifying prior transactions).
5. **`detect_contradictions`** — run the six deterministic detectors.
6. **`detect_injection` (union)** — combine upload-time and analysis-time injection signals.
7. **`score_evidence`** — strength-weighted score → recommendation.
8. **Mint + verify claims** — for SATISFIED requirements only, mint a templated claim and ground it; ungroundable → BLOCKED.
9. **`apply_gate`** — map the whole picture to a review gate.

The output is a `CaseAnalysisResult` carrying requirements, timeline, contradictions, score, recommendation, claims, and gate.

---

## 3. Module layout

| Layer | Modules | Responsibility |
|---|---|---|
| **API** | `src/api/app.py`, `src/api/routes/{cases,demo}.py` | ASGI app, CORS, error mapping, route handlers, client selection |
| **Orchestrator** | `src/orchestrator/{case_service,analysis,gate}.py` | The three-phase pipeline; the pure decision function; the review gate |
| **Extraction** | `src/extraction/{extractor,llm_client,prompts,schemas}.py` | LLM/mock client, prompt isolation, structured extraction schemas |
| **Ingestion** | `src/ingestion/` (csv/json/pdf/txt parsers, `pipeline.py`) | Parse uploaded bytes to text/records; no filesystem writes |
| **Verification** | `src/verification/{classifier,requirement_engine,ce30,contradiction,claim_verifier,timeline_builder}.py` | All deterministic decision logic |
| **Scoring** | `src/scoring/scorer.py` | Strength-weighted score → recommendation |
| **Packaging** | `src/packaging/razorpay_mapper.py` | Verified-claims-only draft package |
| **Domain** | `src/domain/{models,enums,rules}.py` | Pydantic models, enums, per-network requirement definitions |
| **Security** | `src/security/{injection,validators}.py` | Injection tripwire, upload validation |
| **Database** | `src/database/{db,migrations,repositories}.py` | Connection-per-operation, self-healing schema, parameterized queries |
| **Frontend** | `src/` | React 19 + Vite workbench (see [UX](ux.md), [Design system](design-system.md)) |

---

## 4. Deterministic vs. AI responsibilities

The boundary, stated as a contract:

| Responsibility | LLM (Gemini 2.5 Flash / MockLLMClient) | Deterministic Python |
|---|---|---|
| Reading messy evidence into facts | **Yes** — its only job | No |
| Requirement satisfaction | No | **Yes** (`requirement_engine.py`) |
| Scoring & recommendation | No | **Yes** (`scorer.py`) |
| Contradiction detection | No | **Yes** (`contradiction.py`) |
| CE 3.0 qualification | No | **Yes** (`ce30.py`) |
| Claim grounding | No | **Yes** (`claim_verifier.py`) |
| Review gating | No | **Yes** (`gate.py`) |
| Provenance / integrity hashing | No | **Yes** (`Provenance.compute_hash`) |

The system runs end to end with **no API key** — `MockLLMClient` is selected automatically when `GEMINI_API_KEY` is absent (`src/api/app.py:41-52`). See [AI architecture](ai-architecture.md) for the full boundary and its rationale.

---

## 5. Persistence

SQLite via `aiosqlite`, using a **connection-per-operation** model (a single shared connection serializes every statement through one thread and poisons the process on a bad state; short-lived connections are correct under concurrency — `src/database/db.py:1-19`). Every connection sets `foreign_keys=ON`, `journal_mode=WAL`, `busy_timeout=5000` (`db.py:34-49`). The DB path is env-configurable via `DISPUTESHIELD_DB` (`db.py:31`).

**Tables** (`src/database/migrations.py`) — the real schema, not the pre-rebuild table names:

| Table | Holds | Lines |
|---|---|---|
| `cases` | Dispute cases | `migrations.py:75-93` |
| `evidence_items` | Uploaded evidence + `raw_content` | `:96-107` |
| `extracted_facts` | Structured facts with provenance | `:110-122` |
| `claims` | Minted claims + status/block reason | `:125-134` |
| `timeline_events` | Ordered events + anomalies | `:137-149` |
| `contradictions` | Detected contradictions | `:152-164` |
| `audit_log` | Per-stage audit records | `:167-179` |

**Schema self-healing.** `CREATE TABLE IF NOT EXISTS` never alters an existing table, so an older on-disk database silently lacked later-added columns and crashed on write. `_reconcile_columns` (`migrations.py:52`), called from `init_db`, idempotently adds any missing nullable columns from the `_ADDED_COLUMNS` ledger. This is covered by `backend/tests/unit/test_migrations.py`. See [Domain model](domain-model.md) for the model↔table mapping.

---

## 6. Request lifecycle (end to end)

```
POST /api/cases/                → create case
POST /api/cases/{id}/evidence   → Phase 1: validate, injection-check, parse, classify, extract, persist
POST /api/cases/{id}/analyze    → Phase 2: pure decision → CaseAnalysisResult (persists claims/contradictions/timeline)
GET  /api/cases/{id}/analysis   → returns analysis (re-runs Phase 2 deterministically)
GET  /api/cases/{id}/package    → Phase 3: compile verified-claims-only draft (action="draft")
GET  /api/cases/{id}/audit      → per-stage audit trail
POST /api/demo/load             → seed 5 demo cases
```

Because Phase 2 is pure, `GET /analysis` re-running the decision is safe and idempotent — it cannot produce a different verdict from the same stored facts.

---

## 7. Security boundaries (summary)

- **Model boundary:** evidence is delimited as untrusted data and never `.format`-interpolated into prompts; LLM output is coerced into Pydantic schemas; injection is a tripwire that forces human review, never a content mutation.
- **File boundary:** uploads are validated (10 MB cap, `%PDF` magic check for declared PDFs) and parsed **in memory** — never written to disk — eliminating path-traversal-on-write.
- **Query boundary:** all data SQL is parameterized; the only string-built SQL is DDL from a code constant.
- **Action boundary:** `action="draft"` is a hard invariant; the system cannot submit.

The full posture, including the honest gap register (no auth/IDOR, PII at rest, evadable denylist, substring grounding), is in [Security](security.md) and [Threat model](threat-model.md).

---

*Next: [AI architecture](ai-architecture.md) for the LLM boundary in depth; [Domain model](domain-model.md) for the data structures; [Evaluation](evaluation.md) for how the deterministic core is measured.*
