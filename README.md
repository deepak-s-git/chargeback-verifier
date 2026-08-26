# DisputeShield 🛡️

**AI Chargeback Evidence Verifier & Packager — an adversarial auditor for card-network disputes.**

*Razorpay AI Buildathon 2026 — Track 02 (AI Risk Manager). Defense-only: DisputeShield compiles a review-ready **draft**; a human decides and submits. It never contacts a card network.*

---

## The Problem
Merchants lose chargebacks not because they lack evidence, but because their evidence is a mess of unstructured PDFs, emails, and CRM exports. Packaging it to meet the strict, pedantic requirements of card networks (Visa CE 3.0, Mastercard 4837) is slow and error-prone.

Current AI tools are *optimistic generators* — they blindly summarize documents, hallucinate facts to make a response look complete, and gloss over glaring contradictions (e.g. the IP in the access log doesn't match the IP in the email). When an auditor asks "where did this fact come from?", they cannot answer.

## The Solution: An Adversarial Auditor
DisputeShield inverts the approach with a **hybrid, deterministic-first architecture**. AI (Gemini 2.5 Flash) is confined to a single job — *extraction*: reading unstructured documents and proposing structured facts. Every **decision** — requirement satisfaction, scoring, contradiction detection, CE 3.0 qualification, gating — is made by strict, deterministic Python. The mantra is **"AI parses, code decides."**

No extracted fact is believed on the model's word: each must **ground** against its source before it can support a claim, and any claim that cannot be grounded is **blocked**, not guessed. If the evidence is weak or contradictory, DisputeShield says so and routes the case to a human. Declining to fight a bad case is treated as a success, not a failure.

### Key properties
- **No invented evidence.** Claims are minted only for satisfied requirements, templated from rule metadata (never model prose), and blocked unless grounded to source bytes.
- **Provenance on every fact.** Each fact carries a `content_hash` (SHA-256 of the source bytes) plus a presence check against the raw content. *(Grounding is hash + case-insensitive substring presence — strong, but presence-checking, not semantic proof; the honest limits are documented in [Security](docs/security.md) §3.2 and [Failure analysis](docs/failure-analysis.md).)*
- **Deterministic contradiction detection.** Six pure-Python detectors cross-check evidence; a contradiction forces mandatory human review regardless of score.
- **Injection-resistant by construction.** Untrusted evidence can never steer a decision — prompt injection is flagged and routed to a human, never allowed to change a verdict.
- **Runs with no API key.** Absent `GEMINI_API_KEY`, a deterministic `MockLLMClient` is selected automatically, so the full engine — and the entire evaluation — runs offline.

## Architecture Overview

Three phases, with the LLM confined to Phase 1 and every decision in Phase 2 pure and deterministic:

```
Phase 1 — Ingest & Extract        Phase 2 — Analyze (pure, no I/O)     Phase 3 — Package
┌───────────────────────────┐    ┌────────────────────────────────┐   ┌──────────────────────┐
│ Unstructured evidence      │    │ requirements → CE 3.0 → timeline │   │ Draft package         │
│  → parse (CSV/JSON/PDF/TXT)│──▶ │  → contradictions → injection    │──▶│  (verified claims only│
│  → AI + regex extraction   │    │  → scoring → grounded claims     │   │   action = "draft")   │
│  → structured facts        │    │  → human-review gate             │   │  → human reviews      │
└───────────────────────────┘    └────────────────────────────────┘   └──────────────────────┘
```
*See [Architecture](docs/architecture.md) for the full pipeline and the deterministic-vs-AI contract.*

## Tech Stack
- **Backend:** FastAPI · Python 3.13 (requires ≥3.11)
- **Data models:** Pydantic v2
- **Database:** SQLite (via aiosqlite; WAL, foreign keys on, env-configurable path)
- **AI/LLM:** Gemini 2.5 Flash at `temperature=0.0`, behind an `LLMClient` protocol with a deterministic mock fallback
- **Frontend:** Vite · React 19 · TypeScript · Tailwind CSS v4 (CSS-first `@theme`, no config file) · lucide-react · axios · oxlint

## Quick Start

**Prerequisites:** Python ≥3.11 and Node.js 18+. No API key is required — the system falls back to a deterministic mock.

**Backend** (from the repo root):
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"          # dependencies live in pyproject.toml
# optional — enables real Gemini extraction; omit to run fully offline on the mock:
# export GEMINI_API_KEY="your-key-here"
uvicorn src.api.app:app --reload --port 8000
```

**Frontend** (in a second terminal):
```bash
cd frontend
npm install
npm run dev                       # Vite dev server on :5173, proxies /api → :8000
```

Then open the workbench at `http://localhost:5173` and click **Load demo** to seed five example cases.

## Evaluation & Benchmarks
DisputeShield ships with a **coherent-by-construction** synthetic benchmark: 200 cases generated deterministically (`seed=42`, 120/40/40 split) from the same rules the engine implements, with the generator asserting the engine's verdict matches each intended label as it writes. Nine archetypes span strong / moderate / weak / insufficient / contradictory / noisy / adversarial evidence.

Held-out **test split** results (run once, after calibration was frozen):

| Configuration | Test accuracy | Contradiction recall | Injection routing |
|---|---|---|---|
| **Full engine** | **100%** (40/40) | 4/4 | forced review |
| Ablation (safety layers off) | 82.5% | 0/4 | not routed |
| Majority baseline (always CONTEST) | 42.5% | — | — |
| *Prior engine on prior (incoherent) dataset* | *22.5%* | — | — |

**Read this honestly:** a full-engine 100% is an *internal-validity / coherence* result — it proves the rules, engine, and labels are mutually consistent with no calibration drift — **not** out-of-distribution generalization to real merchant evidence. The substantive signals are the **ablation delta** (−17.5 pts, and the ablated engine misses *every* contradiction and injection), the **majority baseline** it beats, and the **before→after** on the same held-out split. See [Evaluation](docs/evaluation.md) and [ADR-009](docs/adrs/ADR-009-evaluation-methodology.md) for the full methodology and metric suite.

Reproduce (no key needed):
```bash
cd backend
venv/bin/python ../scripts/run_evaluation.py --split validation --mode full
```

## Project Structure
```text
chargeback-verifier/
├── backend/
│   ├── src/
│   │   ├── api/            # FastAPI app + routes (entry: src.api.app:app)
│   │   ├── domain/         # Pydantic models, enums, network rules
│   │   ├── ingestion/      # CSV/JSON/PDF/TXT parsers
│   │   ├── extraction/     # LLM client (Gemini + mock), prompts, extractor
│   │   ├── verification/   # requirements, CE 3.0, timeline, contradictions, grounding
│   │   ├── scoring/        # strength-weighted scorer
│   │   ├── security/       # injection detection, upload validators
│   │   ├── orchestrator/   # analysis (pure), case service, review gate
│   │   ├── packaging/      # draft-only Razorpay mapper
│   │   └── database/       # aiosqlite, migrations, repositories
│   ├── evaluation/         # harness, dataset, metrics, reports (git-ignored)
│   ├── tests/              # pytest suite
│   ├── scripts/            # contract_check.py, smoke_demo.py
│   └── pyproject.toml
├── frontend/               # Vite + React 19 + TS + Tailwind v4 workbench
│   └── src/                # App.tsx, components/, lib/ (api, status intents, types)
├── scripts/                # generate_dataset.py, run_evaluation.py
├── docs/                   # full documentation suite (see below)
│   └── adrs/               # Architecture Decision Records (ADR-001 … ADR-012)
└── README.md
```

## Documentation
- [Problem statement](docs/problem.md) · [Product](docs/product.md)
- [Re-architecture report (before → after)](docs/rearchitecture-report.md)
- [System architecture](docs/architecture.md) · [AI architecture](docs/ai-architecture.md) · [Domain model](docs/domain-model.md)
- [Evaluation](docs/evaluation.md) · [Failure analysis](docs/failure-analysis.md)
- [Security](docs/security.md) · [Threat model](docs/threat-model.md)
- [UX](docs/ux.md) · [Design system](docs/design-system.md)
- [Architecture Decision Records](docs/adrs)

## License
MIT License
