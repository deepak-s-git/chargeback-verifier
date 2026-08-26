# ADR-005: Mandatory Human-in-the-Loop

## Context
Chargeback dispute responses are financially material. Submitting incorrect, contradictory, or fabricated evidence can result in compliance violations, fines from card networks, and loss of merchant trust. Fully autonomous AI systems in this domain present an unacceptable risk profile.

## Decision
The system will enforce a **Mandatory Human-in-the-Loop** policy.

### Rules:
1. **No Auto-Submit:** The system will *never* autonomously submit evidence to a payment gateway or card network.
2. **Human Review Gate:** All packaged responses and dispute scores must go through a human review interface.
3. **'Insufficient Evidence' is a Feature:** The system is explicitly designed to declare 'insufficient evidence' or 'contradictory evidence' and halt processing. This is treated as a successful safety check, not a system failure.

## Consequences
- The product serves as a highly advanced "copilot" or "auditor" for dispute analysts, vastly reducing their workload but keeping them in authority.
- Design of the UI must prioritize clear explanation of the system's reasoning and highlighted provenance for all facts.

## Amendment (2026-08-26)

This ADR was realized in code exactly as written; the rebuild made each rule a concrete, testable invariant:

- **No auto-submit is structural, not a policy.** The compiled package's `action` is a hardcoded `"draft"` with no `"submit"` code path anywhere in the repo (`src/packaging/razorpay_mapper.py:60`). It cannot be flipped by configuration or by a prompt.
- **The review gate is deterministic.** `apply_gate(...)` (`src/orchestrator/gate.py:58-67`) forces `MANDATORY_REVIEW` on any injection flag, any contradiction, or any blocked claim — regardless of score. A CONTEST recommendation still routes through a human.
- **"Insufficient / abstain" is a first-class verdict.** INSUFFICIENT and ABSTAIN are real recommendation outputs the engine emits and the evaluation scores (see [docs/evaluation.md](../evaluation.md)); declining to fight is a success path, not an error.
- **Provenance surfaces to the reviewer.** Every verified claim carries `[EV-…]` citations and a content hash (`razorpay_mapper.py:20-36`), and the frontend renders provenance chips so the analyst sees *why* before they act (see [docs/ux.md](../ux.md)).

The one honest gap: there is no authentication yet, so "human review" is procedural, not access-controlled (tracked in [docs/security.md](../security.md) §7 #1). See also [ADR-008](ADR-008-deterministic-first.md).
