# ADR-002: Dispute Category Selection - Visa 10.4 + Mastercard 4837

## Context
We need to select ONE narrow dispute category to optimize our verification and packaging logic. Broadly targeting all dispute reason codes dilutes the effectiveness of the system and makes evaluating the AI components difficult. Options considered were:
- 13.1: Merchandise/Services Not Received
- 13.7: Cancelled Recurring Transaction
- 13.3: Not as Described or Defective Merchandise
- 10.4 / 4837: Fraud / Unauthorized Environment (for Digital Goods)

## Decision
We selected **Visa 10.4 + Mastercard 4837 (Fraud/Unauthorized for digital goods)** as our single focus category.

### Rationale:
1. **High Volume:** It accounts for 60-70% of digital goods chargebacks.
2. **Rich Evidence Requirements:** Requires complex evidence artifacts including IP addresses, device identifiers, 3DS authentication logs, and Compelling Evidence (CE) 3.0 metrics.
3. **Well Documented:** Best-documented category by card networks, providing unambiguous rules for evaluation.
4. **High AI Value:** Demands semantic matching (e.g., identity linkage, behavioral analysis) where LLMs excel.
5. **Clear Ground Truth:** Makes it possible to establish objective ground truth for system evaluation.

## Consequences
- The system is narrowly focused on this specific category but is deeply defensible.
- The judging panel cannot dismiss the solution as being "too broad" or "shallow."
- Evidence processing rules and LLM prompts will be highly tailored to digital goods fraud.
