# ADR-003: Evidence Schema Design

## Context
Merchant evidence is highly varied in format, including CSV files, PDF documents, email threads, and screenshots. To process this systematically, we need a unified, canonical schema that treats all evidence types as queryable objects without losing track of their origins.

## Decision
Every piece of evidence will be modeled as a first-class object with the following schema:
- `evidence_id`: Unique identifier.
- `source_type`: Type of the original document (e.g., CSV, PDF, EMAIL).
- `source_file`: Reference to the original file.
- `source_location`: Specific location within the file (page number, row index, bounding box).
- `timestamp`: Time of ingestion or extraction.
- `actor`: User or system component that ingested it.
- `extracted_facts`: List of typed facts (e.g., IP_ADDRESS, DEVICE_ID, TIMESTAMP).
- `confidence`: Confidence score of the extraction (0.0 to 1.0).
- `provenance`: A composite object containing file reference, location, and a content hash.

### Fact Typing
Facts are strongly typed (e.g., `IP_ADDRESS`, `DEVICE_ID`, `TIMESTAMP`) to allow for strict deterministic validation. The extraction method (e.g., deterministic, regex, LLM) is recorded alongside every fact.

## Consequences
- Evidence is never treated as a single opaque blob.
- Every extracted fact is strictly traceable back to its source document and location.
- The extraction method is recorded for auditing and debugging, enhancing transparency.
- Complex downstream rules can reliably operate on strongly typed facts.

## Amendment (2026-08-26)

The intent held; the field layout as-built differs slightly from the sketch above (`src/domain/models.py`, see [docs/domain-model.md](../domain-model.md)):

- **`Provenance`** is `source_file` + `source_location` + `content_hash` (a SHA-256 of the source bytes). There is no bounding-box field; `source_location` is a free-text locator.
- **`ExtractedFact`** carries `type`, `value`, `confidence` (0–1), `extraction_method` (DETERMINISTIC / REGEX / LLM / OCR), and its `provenance` — matching the "extraction method recorded alongside every fact" intent.
- **`EvidenceItem`** carries `source_type` *and* a `semantic_type` (e.g. PAYMENT_PROOF), `raw_content`, `created_at`, and its list of facts. Per-event `actor` / `ip_address` live on `TimelineEvent`, not on the evidence object.
- The `content_hash` is what makes grounding possible: a claim's fact must hash-match its source bytes (see [docs/ai-architecture.md](../ai-architecture.md)).
