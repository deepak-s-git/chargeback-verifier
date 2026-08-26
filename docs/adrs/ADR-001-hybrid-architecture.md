# ADR-001: Hybrid Deterministic + AI Architecture

## Context
We need to process merchant evidence for chargeback disputes. Processing unstructured data (PDFs, emails, free-text CSVs) is inherently fuzzy and traditionally requires significant human effort. Pure Large Language Model (LLM) approaches are capable of understanding unstructured documents, but they frequently hallucinate facts and cannot guarantee provenance (i.e., tying a fact back to its exact source). Conversely, pure deterministic or rule-based approaches cannot robustly understand the diverse and unstructured nature of merchant evidence.

## Decision
We will implement a **Hybrid Architecture** that strictly separates responsibilities:
- **Deterministic Layer:** Handles all validation, business rules, scoring logic, workflow gating, and audit logging. This layer is entirely code-based (Python).
- **AI Layer:** Responsible for document understanding, entity extraction, semantic classification, and natural language contradiction detection.

## Consequences
- **Increased Complexity:** Building an abstraction that separates these concerns requires more upfront design than a pure LLM workflow.
- **Dramatically Higher Reliability:** Every AI output is independently validated by the deterministic layer. The LLM is used as an extraction engine, not a decision engine.
- **Guaranteed Provenance:** Provenance is enforced by the architecture, not by relying on prompt engineering (e.g., "tell me where you found this"). The deterministic layer verifies that extracted entities exist in the source documents.
