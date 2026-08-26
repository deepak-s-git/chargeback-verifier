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
