# The Problem: Why Merchants Lose Chargebacks

## The Reality of Dispute Management
Merchants frequently lose chargeback disputes—not because they lack the necessary evidence to prove the transaction was legitimate, but because of **how** that evidence is presented. 

Card networks (Visa, Mastercard) have extremely strict, specific requirements for what constitutes compelling evidence (e.g., Visa CE 3.0). However, the evidence merchants possess is almost entirely unstructured:
- Messy PDF receipts
- Email threads with customers
- Screenshots of delivery confirmations
- Free-text CSV exports from internal CRM systems

When a merchant receives a chargeback, analysts must manually sift through these disparate documents, find the relevant data points (IP addresses, device IDs, exact timestamps), verify they match, and package them according to the exact specifications of the network reason code.

## The Flaw in Current "AI" Solutions
The current wave of AI tools aimed at chargebacks are largely **Optimistic Generators**. 
They take a pile of merchant documents, feed them into an LLM, and prompt it to "write a dispute response." 
These systems:
- Blindly package whatever exists in the documents.
- Gloss over contradictions (e.g., a mismatched shipping address).
- Frequently hallucinate facts to make the dispute response look "better" or more complete.
- Cannot guarantee the provenance of any claim (if an auditor asks "where did you get this IP address?", the system cannot point to the exact file and line).

## The DisputeShield Approach: The Adversarial Auditor
DisputeShield takes the opposite approach. We are building an **Adversarial Auditor**.

Instead of optimistically generating a response, DisputeShield rigorously verifies the evidence *before* submission.
1. **Extracts:** Finds all relevant facts using AI, mapping them to a strict schema.
2. **Verifies:** Deterministically cross-checks facts across documents to find contradictions.
3. **Audits:** Ensures every single piece of extracted data has strict, cryptographic provenance tying it back to the original source file.
4. **Gates:** If the evidence is insufficient or contradictory, the system halts and flags it. We consider refusing to submit a bad case a feature, not a failure.

By combining the natural language understanding of AI with the rigorous validation of deterministic code, DisputeShield ensures that only mathematically sound, fully proven cases are sent to the card networks.
