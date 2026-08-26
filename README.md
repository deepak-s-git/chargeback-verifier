# DisputeShield 🛡️

**AI Chargeback Evidence Verifier & Packager**

## The Problem
Merchants lose millions in chargebacks not because they lack evidence, but because their evidence is a mess of unstructured PDFs, emails, and CRM exports. Packaging this data to meet the strict, pedantic requirements of card networks (like Visa CE 3.0) is a slow, error-prone manual process.

Current AI tools are "optimistic generators"—they blindly summarize documents, often hallucinate facts, and fail to notice glaring contradictions (e.g., the IP address in the log doesn't match the IP in the email). When network auditors ask for the provenance of a data point, these tools fail.

## The Solution: An Adversarial Auditor
DisputeShield takes a radically different approach. We utilize a **Hybrid Deterministic + AI Architecture**. We use AI (Gemini 2.5 Flash) strictly as an extraction engine to read unstructured documents. We then use strict deterministic Python code to aggressively audit, cross-check, and verify every single extracted fact. 

If evidence is weak or contradictory, DisputeShield flags it. We don't invent evidence; we mathematically prove the provenance of the evidence you have.

### Key Differentiators
- **Zero Hallucination Guarantee:** Every extracted fact is deterministically verified against the source text.
- **Strict Provenance:** Every claim is cryptographically tied to its exact source file and location.
- **Contradiction Detection:** Automatically finds conflicting evidence across different documents.
- **Targeted Precision:** Built specifically for Visa 10.4 / Mastercard 4837 (Fraud/Unauthorized for Digital Goods).

## Architecture Overview

```
[ Unstructured Evidence ] --> [ AI Extraction (Gemini) ] --> [ Structured Facts ]
                                                                     |
                                                                     v
[ Final Package ] <-- [ Scoring & Gating ] <-- [ Deterministic Verification ]
```
*(See [Architecture](docs/architecture.md) for full details)*

## Tech Stack
- **Backend:** FastAPI, Python 3.11+
- **Data Models:** Pydantic v2
- **Database:** SQLite (via aiosqlite)
- **AI/LLM:** Gemini 2.5 Flash
- **Frontend:** TypeScript / React (Planned)

## Quick Start

```bash
# Clone the repository
git clone https://github.com/your-org/disputeshield.git
cd disputeshield

# Set up virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set your API keys
export GEMINI_API_KEY="your-key-here"

# Run the FastAPI server
uvicorn main:app --reload
```

## Evaluation & Benchmarks
DisputeShield includes a rigorous synthetic benchmark of 200 curated chargeback cases to prove its efficacy against strong, weak, contradictory, and adversarial (prompt injection) evidence.
See [Synthetic Benchmark Design](docs/adrs/ADR-006-synthetic-benchmark.md).

## Project Structure
```text
disputeshield/
├── backend/            # FastAPI application
│   ├── api/            # Routes and controllers
│   ├── core/           # Deterministic verification and rules engine
│   ├── models/         # Pydantic schemas and DB models
│   └── services/       # AI integration and external services
├── docs/               # Documentation and Architecture
│   └── adrs/           # Architecture Decision Records
├── tests/              # Pytest suite and synthetic benchmarks
└── README.md
```

## Documentation
- [Problem Statement](docs/problem.md)
- [System Architecture](docs/architecture.md)
- [Threat Model](docs/threat-model.md)
- [Architecture Decision Records (ADRs)](docs/adrs)

## License
MIT License
