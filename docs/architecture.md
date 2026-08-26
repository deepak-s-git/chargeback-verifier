# Architecture

DisputeShield employs a Hybrid Deterministic + AI architecture, ensuring the flexibility of LLMs for document understanding is firmly grounded by the strict reliability of deterministic code.

## System Overview

```mermaid
graph TD
    A[Merchant Evidence (PDF, CSV, Email)] -->|Ingestion| B(Ingestion Engine)
    B --> C{AI Extraction Layer}
    C -->|Unstructured Data| D[Gemini 2.5 Flash]
    D -->|Structured Facts| C
    C --> E(Deterministic Verification Layer)
    E -->|Rules & Logic| F[Scoring & Gating Engine]
    F -->|Contradiction/Insufficient| G[Mandatory Review Flag]
    F -->|Verified & Strong| H[Response Packager]
    H --> I[Human-in-the-Loop Review UI]
    I --> J(Final Submission to Gateway)
    
    E -.-> K[(SQLite Database)]
```

## Pipeline Flow

1. **Ingestion:** Raw files are uploaded, text is extracted (OCR if necessary), and mapped to internal file records.
2. **Extraction (AI Layer):** Gemini 2.5 Flash processes the text, searching for specific entities (IPs, emails, tracking numbers) relevant to Visa 10.4 / MC 4837. It outputs Pydantic-validated JSON.
3. **Verification (Deterministic Layer):** Python code takes the JSON facts and runs cross-document checks. It ensures that IP addresses match, timestamps make chronological sense, and provenance hashes are generated.
4. **Scoring & Gating:** The verified facts are scored against network requirements. If contradictions are found, the case is immediately flagged. Otherwise, a confidence score (0-100) is assigned.
5. **Packaging:** For valid cases, the system generates a structured dispute response package, ready for human review.

## Deterministic vs AI Layer Separation

The core philosophy of this architecture is **never trusting the AI with decisions.**

| Responsibility | AI Layer (Gemini) | Deterministic Layer (Python) |
| :--- | :--- | :--- |
| **Document Parsing** | Yes (Semantic understanding) | No |
| **Fact Extraction** | Yes (Finds the IP in the text) | No |
| **Fact Validation** | No | Yes (Regex check, cross-matching) |
| **Decision Making** | No | Yes (Rules engine, scoring) |
| **Provenance tracking**| No | Yes (Cryptographic hashing of source) |

## Database Schema Overview

We use SQLite (via `aiosqlite`) for fast, local, lightweight storage suitable for the buildathon.

- **Disputes:** `id`, `amount`, `currency`, `reason_code`, `status`, `score`
- **Documents:** `id`, `dispute_id`, `filename`, `file_type`, `content_hash`, `raw_text`
- **ExtractedFacts:** `id`, `document_id`, `fact_type` (Enum), `fact_value`, `confidence`, `provenance_location`
- **AuditLogs:** `id`, `dispute_id`, `action`, `actor`, `timestamp`

## Security Boundaries
- **AI Boundary:** All prompts are parameterized. LLM output is strictly coerced into Pydantic models. Any output failing schema validation is rejected (preventing prompt injection from leaking arbitrary text into the system state).
- **File Boundary:** Uploaded documents are sandboxed and only parsed for text. No execution of embedded scripts or macros.
