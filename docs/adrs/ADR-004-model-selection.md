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
