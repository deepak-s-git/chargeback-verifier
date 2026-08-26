# ADR-004: LLM Selection - Gemini 2.5 Flash

## Context
The AI layer requires a Large Language Model (LLM) for document understanding, entity extraction, semantic classification, and natural language contradiction detection. We evaluated several models including GPT-4o, GPT-4o-mini, Claude 3.5 Sonnet, Gemini 2.5 Flash, and Gemini 2.5 Pro.

## Decision
We will use **Gemini 2.5 Flash** as our primary model, implemented behind an abstraction layer to ensure swappability.

### Rationale:
1. **Speed:** Offers fast inference, crucial for batch evaluating 200 synthetic cases efficiently.
2. **Structured Output:** Provides excellent support for structured, JSON-based outputs which is essential for our evidence schema.
3. **Cost-Effective:** Ideal for a buildathon budget without sacrificing required capabilities.
4. **Pydantic Support:** Seamlessly supports Pydantic schema-constrained outputs, enabling strict validation of the LLM's responses.

## Consequences
- All LLM interactions must go through a single interface/abstraction layer.
- The system is not locked into Gemini; if a better model is required later (e.g., Gemini 2.5 Pro for harder edge cases), swapping it is a configuration change, not a code rewrite.

## Amendment (2026-08-26)

Three clarifications on how this landed in code:

1. **The model's job is extraction only.** The Context above mentions "natural language contradiction detection" as an AI-layer task; that was reclassified to the deterministic layer (see [ADR-001 amendment](ADR-001-hybrid-architecture.md) and [ADR-008](ADR-008-deterministic-first.md)). Gemini 2.5 Flash is used solely to propose structured facts during ingestion.
2. **Deterministic by default.** The abstraction is the `LLMClient` Protocol (`src/extraction/llm_client.py`); Gemini runs at **temperature 0.0** against a structured schema, and a `MockLLMClient` is selected automatically when `GEMINI_API_KEY` is absent (`src/api/app.py:41-52`). The system is fully operational — and fully evaluable — with no key.
3. **The key is never logged** — only the client class name and model are emitted. See [docs/security.md](../security.md) §3.4.
