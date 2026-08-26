# ADR-008: Deterministic-First, LLM-Optional

> **Status:** Accepted 2026-08-26. Sharpens [ADR-001](ADR-001-hybrid-architecture.md) and [ADR-004](ADR-004-model-selection.md).

## Context

[ADR-001](ADR-001-hybrid-architecture.md) committed us to a hybrid architecture but left one thing under-specified: *how much* of the load-bearing work the LLM is allowed to touch, and what happens when there is no model available at all. During the rebuild this ambiguity mattered, because the original system had drifted toward using the model for judgement calls (semantic contradiction detection, implicit scoring cues) that are safety-critical and must be reproducible. A chargeback decision that changes because a model was retrained, rate-limited, or absent is not an acceptable failure mode for an evidence-integrity system.

We needed a single, unambiguous principle that says where intelligence is allowed and where correctness is mandatory.

## Decision

We adopt **deterministic-first, LLM-optional** as the governing principle, summarized as **"AI parses, code decides."**

1. **Every decision is pure deterministic Python.** Requirement satisfaction, scoring, CE 3.0 qualification, contradiction detection, injection routing, and gating are computed by `analyze_evidence(...)` (`src/orchestrator/analysis.py:76`) — a side-effect-free function whose output depends only on grounded facts, network rules, and fixed thresholds. No network call, no I/O, no model in this path.
2. **The LLM is confined to extraction.** Its sole job is to *propose* structured facts from unstructured evidence during ingestion. It never sees a "should we contest?" prompt, and its proposals are untrusted until they ground against source bytes (`src/verification/claim_verifier.py`).
3. **The model is optional.** When `GEMINI_API_KEY` is unset, a deterministic `MockLLMClient` is selected automatically (`src/api/app.py:41-52`). The full system — and the entire evaluation — runs correctly with no model in the loop.

## Consequences

- **Reproducibility.** The same case always produces the same verdict, because the decision is a pure function. The evaluation is deterministic and runs with no credentials (see [ADR-009](ADR-009-evaluation-methodology.md)).
- **Injection cannot flip a verdict.** Because the model has no say in the decision, the worst a prompt-injection payload can do is trip a detector and force human review — never change a recommendation (`src/orchestrator/gate.py:58-67`; see [docs/security.md](../security.md) §3.1).
- **Auditability.** Every decision is traceable to code and grounded facts, not to a model's opaque state. This is what makes the [threat model](../threat-model.md) and [failure analysis](../failure-analysis.md) tractable to write honestly.
- **The cost is expressiveness.** Deterministic detectors are pattern-specific and can miss cases a language model might catch (documented candidly in [failure-analysis.md](../failure-analysis.md) §3, §5). We accept that trade: a miss routes to a human; a model hallucination could fabricate a dispute. The former is recoverable, the latter is not.
- **Realized across the codebase**, not aspirational: see [docs/architecture.md](../architecture.md) (deterministic-vs-AI contract table) and [docs/ai-architecture.md](../ai-architecture.md).
