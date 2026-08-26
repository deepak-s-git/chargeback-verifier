# ADR-001: Hybrid Deterministic + AI Architecture

> **Status:** Accepted, **amended 2026-08-26** (see Amendment). Refined by [ADR-008](ADR-008-deterministic-first.md).

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

## Amendment (2026-08-26)

The rebuild sharpened the boundary this ADR set out. Two corrections to the original wording:

1. **Contradiction detection is now deterministic, not AI.** The Decision section above listed "natural language contradiction detection" under the AI Layer. That is no longer accurate: all six contradiction detectors are pure deterministic Python (`src/verification/contradiction.py`), because a safety-critical check must be reproducible and auditable, not model-dependent. The AI Layer's responsibility is now **extraction only**.
2. **The system runs with no model at all.** A deterministic `MockLLMClient` is the automatic fallback when `GEMINI_API_KEY` is unset (`src/api/app.py:41-52`), so the decision engine — and the entire evaluation — is exercised without any LLM in the loop.

The principle is unchanged and was strengthened: the LLM is an extraction engine, never a decision engine. This is formalized as "deterministic-first, LLM-optional" in [ADR-008](ADR-008-deterministic-first.md); see also [docs/ai-architecture.md](../ai-architecture.md) and [docs/architecture.md](../architecture.md).
