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
