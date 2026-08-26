# Product

**DisputeShield — a chargeback evidence intelligence platform that decides what the evidence actually supports, and refuses to claim more.**

*Scope: the product thesis, the user, the problem, and what the system does and deliberately does not do. Verified 2026-08-26 against the rebuilt engine. Companion documents: [Architecture](architecture.md) · [AI architecture](ai-architecture.md) · [Evaluation](evaluation.md) · [UX](ux.md) · [Re-architecture report](rearchitecture-report.md).*

---

## 1. The one-paragraph pitch

When a cardholder disputes a transaction, the merchant has a short, hard deadline to assemble evidence that satisfies a specific card-network reason code — and most merchants either miss the requirements, submit contradictory material, or overstate what their evidence proves. DisputeShield ingests the merchant's fragmented evidence (logs, invoices, e-mails, screenshots, payment records), extracts structured facts from it, and then **deterministically** determines which of the network's evidence requirements are genuinely supported, which are missing, and which are contradicted. It produces a **bounded, cited, human-reviewable draft package** — and it will abstain rather than fabricate. The guiding principle is literal: **AI parses, code decides, and the system never invents evidence.**

---

## 2. Track and framing

Built for the **Razorpay AI Buildathon 2026 — Track 02 (AI Risk Manager)**. The risk being managed is not fraud detection at authorization time; it is **representment risk** at dispute time: the risk that a merchant (or the platform acting on their behalf) submits a chargeback rebuttal that is unsupported, self-contradictory, or non-compliant with network evidence rules — wasting the one representment attempt, incurring fees, and eroding the platform's standing with the networks.

DisputeShield treats that risk as an **evidence-integrity** problem, not a persuasion problem. It does not try to win disputes with better rhetoric. It tries to ensure that every claim in a rebuttal is backed by evidence that actually exists in the merchant's submission, mapped to the requirement it satisfies.

---

## 3. Who it is for

The primary user is a **risk or dispute-operations analyst** at a payment platform or acquirer — the person who today opens a chargeback, reads through a merchant's uploaded evidence, cross-references it against Visa/Mastercard reason-code requirements, and decides whether there is a defensible case. That work is:

- **High-volume and repetitive** — the same requirement checklists, applied case after case.
- **Error-prone under time pressure** — reason-code rules are intricate (Visa's Compelling Evidence 3.0 alone has date-window, matching-element, and anchor constraints), and the response deadline is measured in days.
- **Consequential** — a wrongly submitted or overclaimed package burns the representment and can be worse than not contesting at all.

DisputeShield is a **decision-support tool for that analyst**, not a replacement for them. It does the mechanical, rules-heavy triage deterministically and reproducibly, and hands the analyst a structured verdict with every claim traced back to its source — so the human spends their judgment on the cases that actually need it.

---

## 4. The problem, precisely

A chargeback rebuttal fails for four recurring reasons. DisputeShield is built to catch each one **before** a package is compiled:

| Failure mode | What goes wrong today | What DisputeShield does |
|---|---|---|
| **Missing requirements** | The merchant submits evidence that doesn't cover a mandatory element of the reason code | Evaluates every requirement for the network/reason code and reports coverage, not just a yes/no |
| **Overclaiming** | The rebuttal asserts things the evidence doesn't actually show | Mints claims only for satisfied requirements, and **blocks** any claim that can't be grounded to source bytes |
| **Contradictions** | Two pieces of evidence disagree (IP mismatch, usage before purchase, amount mismatch), undermining the whole package | Runs six deterministic contradiction detectors and forces the case to human review on any hit |
| **Adversarial / poisoned evidence** | Uploaded content contains instructions intended to manipulate an automated reviewer | Flags injection attempts and routes to mandatory human review — evidence never steers the decision |

---

## 5. What the system produces

For each case, DisputeShield yields:

1. **A requirement ledger** — every network requirement for the reason code, each marked SATISFIED / PARTIALLY_SATISFIED / MISSING, with the specific fact types that satisfied or are missing from it.
2. **A recommendation** — one of `CONTEST`, `REVIEW`, `INSUFFICIENT`, or `ABSTAIN`, derived from a transparent strength-weighted score, never from model prose.
3. **A review gate** — `READY`, `NEEDS_REVIEW`, `MANDATORY_REVIEW`, or `NOT_RECOMMENDED`, with explicit reasons.
4. **A verified evidence timeline** with anomaly flags.
5. **A contradiction report.**
6. **A bounded draft package** — a network-shaped payload plus a plain-language explanation letter assembled *only* from verified claims, each carrying an `[EV-…]` citation, with `action` hardcoded to `"draft"`.
7. **An audit trail** — every pipeline stage recorded with the model used and a decision record.

Everything the analyst sees is traceable. If the evidence isn't there, the package says so rather than inventing it.

---

## 6. The recommendation taxonomy (what the verdicts mean)

| Recommendation | Meaning | Analyst action |
|---|---|---|
| **CONTEST** | Requirements are strongly supported and no blocking issue was found | Review the draft, then decide to represent |
| **REVIEW** | There is a real case, but something needs a human eye (a contradiction, an injection flag, or a borderline score) | Investigate the flagged reason before proceeding |
| **INSUFFICIENT** | Some support exists but it falls short of the network's bar | Request more evidence from the merchant, or decline |
| **ABSTAIN** | There is not enough grounded evidence to say anything | Do not contest on this basis |

The distinction between `CONTEST` and `REVIEW` is deliberately conservative: **any** contradiction or injection signal pulls a case into `REVIEW` regardless of how strong the score is, because a high score built on contradictory evidence is exactly the kind of package that should never be auto-approved.

---

## 7. Design commitments (the non-negotiables)

These are product commitments, enforced in code and documented across the companion docs:

- **Never invent evidence.** Every substantive claim is traceable to a piece of submitted evidence or it is blocked. There is no "fill in the plausible gap." See [AI architecture](ai-architecture.md).
- **Deterministic where correctness matters.** The recommendation, score, gate, requirement evaluation, contradiction detection, and CE 3.0 qualification are pure deterministic Python. The LLM's only job is reading messy input into structured facts. See [Architecture](architecture.md).
- **Defense-only.** The system compiles a draft for a human; it can never submit a dispute to a network. `action="draft"` is a hard invariant. See [Security](security.md).
- **Humans where consequences matter.** Contradictions, injection, and ungroundable claims force human review by construction, not by convention.
- **Honest about limits.** The system abstains loudly, and the documentation ([Security](security.md), [Failure analysis](failure-analysis.md)) records what it does *not* yet do.

---

## 8. What DisputeShield is *not*

- It is **not an auto-submitter.** It never files a representment; it prepares one for review.
- It is **not a fraud scorer.** It does not judge whether the original transaction was fraudulent; it judges whether the evidence supports the merchant's rebuttal of the dispute.
- It is **not a persuasion engine.** It does not generate rhetorical arguments; it assembles cited, verified statements of fact.
- It is **not a black box.** There is no point at which an unexplained model output determines the outcome. Every verdict decomposes into requirements, facts, and rules a human can inspect.

---

*For how these commitments are realized in code, see [Architecture](architecture.md) and [AI architecture](ai-architecture.md). For evidence that they hold up under measurement, see [Evaluation](evaluation.md). For the full story of how the system was rebuilt to reach this design, see the [Re-architecture report](rearchitecture-report.md).*
