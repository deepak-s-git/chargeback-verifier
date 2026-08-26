# Security

**DisputeShield — security posture, controls, and honest limitations.**

*Scope: the rebuilt DisputeShield backend (`backend/src`) and its data flow. Every control below is verified against the current source with `path:line` citations. Verified 2026-08-26 against the deterministic-first engine. Companion documents: [Threat model](threat-model.md) · [Architecture](architecture.md) · [AI architecture](ai-architecture.md).*

---

## 1. Posture in one paragraph

DisputeShield ingests **untrusted merchant evidence** (PDFs, CSVs, JSON, e‑mails, logs) and must never let that evidence steer its own decisions, never fabricate facts, and never act on the merchant's behalf. The design achieves this structurally: the LLM is confined to *proposing* extracted facts during ingestion, and every load‑bearing decision — requirement satisfaction, scoring, contradiction detection, CE 3.0 qualification, gating — is a **pure, deterministic Python function** (`src/orchestrator/analysis.py:76`) whose output is derived only from facts that survive cryptographic grounding against their source bytes (`src/verification/claim_verifier.py`). The system compiles a **draft package only** and can never auto‑submit a dispute (`src/packaging/razorpay_mapper.py:60`). This is the platform's strongest security property, and it is real.

What follows is an honest accounting: the controls that exist, the deliberate design choices behind them, and a prioritized register of the gaps that remain. Because this is a buildathon prototype optimized for a defensible *decision core* rather than a hardened deployment, several production controls (authentication, encryption at rest, rate limiting) are intentionally deferred and documented in §7 rather than silently omitted.

---

## 2. Security principles (and where they live in code)

| Principle | Enforcement | Location |
|---|---|---|
| **Never invent evidence** | Claims are minted only for satisfied requirements, templated from requirement metadata (no LLM prose), and BLOCKED unless grounded to source bytes | `src/orchestrator/analysis.py:113-118`, `src/verification/claim_verifier.py:40-77` |
| **Treat all evidence as untrusted input** | Evidence is data, never instructions; injection is detected and routed to a human, decisions come from deterministic code | `src/security/injection.py`, `src/orchestrator/analysis.py:76` |
| **Defense‑only, never auto‑submit** | Package `action` is hardcoded `"draft"`; there is no `"submit"` code path | `src/packaging/razorpay_mapper.py:60` |
| **Humans where consequences matter** | Any injection, contradiction, or blocked claim forces mandatory human review | `src/orchestrator/gate.py:58-67` |
| **Fail closed on missing evidence** | Ungroundable or evidence‑less claims are BLOCKED, not guessed | `src/verification/claim_verifier.py:53-76` |

---

## 3. Controls in place

### 3.1 Deterministic decision core (the primary control)
The LLM (`Gemini 2.5 Flash`, or a deterministic `MockLLMClient` when no key is set) only runs during **extraction** and only *proposes* structured facts. It never sees a "should we contest?" prompt and its output is never trusted verbatim — each proposed fact must ground before it can support a claim. The decision function `analyze_evidence(...)` (`src/orchestrator/analysis.py:76`) is side‑effect‑free and derives its verdict purely from grounded facts, network rules, and thresholds. Prompt injection therefore cannot change a recommendation; at worst it forces the case to human review (§3.5).

### 3.2 Output integrity — "verified claims only"
- Claim descriptions are **templated**, not model‑authored: `f"{req.name} is satisfied per {req.source_reference}."` (`src/orchestrator/analysis.py:113-118`).
- **Grounding** requires two independent checks (`src/verification/claim_verifier.py:26-37`): integrity — `fact.provenance.content_hash == sha256(evidence.raw_content)`; and presence — the fact's value must appear in the source text. Failing either → the claim is **BLOCKED** (`:53-56, 61-64, 71-76`).
- The compiled package and the Razorpay payload are built **only from VERIFIED claims** (`src/packaging/razorpay_mapper.py:20-36, 49, 70-74`); the explanation letter is assembled solely from verified claims with `[EV-…]` citations, and explicitly says so when none exist (`:20-36`).
- **Auto‑submit is impossible:** `action` is a hardcoded `"draft"` invariant with no submit path (`razorpay_mapper.py:60`).
- The extractor delimits evidence as data and runs Gemini at `temperature=0.0` against a structured schema (`src/extraction/extractor.py:35-42`, `src/extraction/llm_client.py:28,38`).

> **Caveat (documented, not hidden):** grounding's presence check is a case‑insensitive **substring** test (`claim_verifier.py:34`), and a claim is VERIFIED if *any one* cited evidence item grounds *any* fact (`:58-69`). This is presence‑checking, not semantic proof; very short/common values can ground trivially. See [Failure analysis](failure-analysis.md) and the remediation register (§7, #9).

### 3.3 SQL safety
Every data query uses `?` placeholders with bound parameter tuples — no value is ever string‑interpolated into SQL. Representative sites: case insert (`src/database/repositories.py:45-64`), read by id (`:93`), evidence+facts (`:132-158`), claims (`:226-236`), timeline (`:276-288`), audit (`:326-338`). The only string‑built SQL is schema DDL whose identifiers come exclusively from the module‑level constant `_ADDED_COLUMNS` (`src/database/migrations.py:38-49, 59, 64`) — never from request input, therefore not injectable. Connections are per‑operation with `foreign_keys=ON`, `journal_mode=WAL`, `busy_timeout=5000` (`src/database/db.py:34-49`). **SQL‑injection risk in the query layer: effectively none.**

### 3.4 Secrets management
- `GEMINI_API_KEY` is read from the environment only (`src/api/app.py:41`, `src/extraction/llm_client.py:16`); absent it falls back to `MockLLMClient` (`app.py:42-44`).
- DB location is env‑overridable via `DISPUTESHIELD_DB` (`src/database/db.py:31`).
- **No `.env` file and no hardcoded secrets exist** in the repo (grep‑verified); `.env*` and `*.db` are git‑ignored (root `.gitignore`).
- The key is **never logged** — only the client class name and model are emitted (`app.py:43,49`).

### 3.5 Prompt‑injection detection (flag‑and‑route, by design)
`detect_injection(text)` (`src/security/injection.py:21`) matches a case‑insensitive regex denylist (`:9-19`) and is applied at two points: on upload (`src/orchestrator/case_service.py:111-119`) and during analysis over each item's `raw_content` (`src/orchestrator/analysis.py:59-73`). On any hit, the gate forces `GateStatus.MANDATORY_REVIEW` regardless of score (`src/orchestrator/gate.py:58-67`).

**Design rationale — why flag, not mutate.** For an *evidence‑integrity* system, silently rewriting untrusted evidence would itself break provenance and chain‑of‑custody: the package must reflect what the merchant actually submitted. So the correct posture is to **preserve the bytes, flag the anomaly, and route to a human** — never to alter evidence in place. Detection is intentionally a tripwire that diverts control to a person, not a content filter. (This also means the `sanitize_evidence_text` helper and `sanitized_text` field are currently unused — see §7 #3; the honest read is that the substantive defense is the deterministic core + human gate, and the denylist is a coarse tripwire, not the primary barrier.)

### 3.6 Upload validation
`validate_file(...)` (`src/security/validators.py:7`, called at `src/orchestrator/case_service.py:104`) enforces a **10 MB** size cap (`:10-12`), rejects empty files (`:14-15`), and checks the `%PDF` magic prefix for content declared as PDF (`:18-19`). Uploaded content is **never written to the filesystem** — it is parsed in memory and persisted to SQLite as TEXT, so there is **no path‑traversal‑on‑write sink**.

### 3.7 Error handling and CORS
A catch‑all returns a generic 500 while logging detail server‑side, so internals and evidence never leak in responses (`src/api/app.py:103-108`); `ValueError` maps to 400 with its message (`:97-100`). CORS is restricted to dev origins `http://localhost:5173` and `http://localhost:3000` (`app.py:80-86`).

---

## 4. Data handling & PII

| State | Location | Protection | Note |
|---|---|---|---|
| In transit (responses) | all routes | generic errors; no stack/internal leak | `app.py:103-108` |
| At rest | `evidence_items.raw_content`, `extracted_facts.value` (SQLite TEXT) | **none — plaintext** | HIGH gap, §7 #2 |
| In logs | structlog → JSON → stdout | raw evidence **deliberately never logged** (`case_service.py:110-112`, `analysis.py:64-65`); no redaction processor | `error=str(exc)` and `file_path` may carry PII, §7 #8, #10 |

Raw evidence in the demo set contains e‑mails and IPs (`src/api/routes/demo.py:95,101,151,157`) and real merchant evidence can contain PANs/OTPs; the at‑rest and no‑auth gaps below therefore compound.

---

## 5. API surface

All routes are unauthenticated (see §7 #1). Full inventory:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness (`app.py:92-94`) |
| POST | `/api/cases/` | Create case (`cases.py:37-41`) |
| GET | `/api/cases/` | List cases (`cases.py:44-48`) |
| GET | `/api/cases/{id}` | Case + evidence incl. `raw_content` (`cases.py:51-60`) |
| POST | `/api/cases/{id}/evidence` | Upload evidence (`cases.py:63-79`) |
| POST | `/api/cases/{id}/analyze` | Run analysis (`cases.py:82-89`) |
| GET | `/api/cases/{id}/analysis` | Analysis, re‑runs analyze (`cases.py:92-94`) |
| GET | `/api/cases/{id}/timeline` | Timeline (`cases.py:97-101`) |
| GET | `/api/cases/{id}/package` | Compile/return package (`cases.py:104-111`) |
| GET | `/api/cases/{id}/audit` | Audit trail (`cases.py:114-118`) |
| POST | `/api/demo/load` | Seed 5 demo cases (`demo.py:221-242`) |
| GET | `/api/demo/status` | Demo‑loaded flag (`demo.py:245-250`) |

---

## 6. Secure‑by‑design decisions worth preserving

1. **LLM is advisory‑only during extraction; the decision core is deterministic.** Injection cannot flip a verdict.
2. **No filesystem writes for uploads.** Content lives in memory → SQLite TEXT, eliminating an entire class of path‑traversal and file‑drop attacks.
3. **Parameterized SQL everywhere**; DDL identifiers come only from a code constant.
4. **Env‑only secrets, key never logged, mock fallback** so the system runs safely with no credentials.
5. **Preserve‑and‑flag over mutate** for untrusted evidence — protects provenance.
6. **`action="draft"` hard invariant** — defense‑only is structural, not a policy checkbox.

---

## 7. Known limitations & remediation register (honest, prioritized)

This is a prototype hardened around its *decision integrity*, not its deployment surface. The following are real and are documented deliberately. Severity reflects impact **if deployed as‑is to an untrusted network**; in the buildathon/demo context (local, single‑operator) the practical risk is lower, but none of these should ship to production unaddressed. See [Threat model](threat-model.md) for attacker scenarios.

### HIGH
1. **No authentication/authorization on any endpoint → IDOR.** Any client can create/read/analyze/package/dump the audit of any `case_id`; case IDs are returned by `GET /api/cases/` (`src/api/` — only CORS middleware, `app.py:80-86`). *Remediation:* auth middleware (API key or session) + per‑principal case ownership checks. Deferred for the demo (no login UI by design).
2. **PII plaintext at rest, served to unauthenticated callers.** `evidence_items.raw_content` (e‑mails/IPs/possible PAN/OTP) is unencrypted (`migrations.py:96-107`, `repositories.py:140-143`) and returned in full by `GET /api/cases/{id}` (`cases.py:58-59`). *Remediation:* field‑level encryption or tokenization at rest + auth (#1) + response‑time masking of sensitive fact types.
3. **Injection sanitization is dead code.** `sanitize_evidence_text`/`sanitized_text` are computed but never consumed (`src/security/injection.py:34-35`). *Remediation (chosen):* keep flag‑and‑route (§3.5 rationale) and **remove the dead helper** to avoid implying a neutralization guarantee that does not exist. The substantive defense remains the deterministic core + human gate.

### MEDIUM
4. **Injection denylist is trivially evadable** — 9 fixed phrases, single‑literal‑space regex, plural‑only, no encoding/homoglyph/translation coverage; upload‑time (`errors="ignore"`) vs analysis‑time (parser `errors="replace"`) decodings can disagree (`injection.py:9-19`; `case_service.py:111` vs parsers). *Remediation:* normalize whitespace/encoding before matching; broaden patterns; treat the denylist as one signal feeding the human‑review gate, not a barrier.
5. **Unbounded upload → memory/DoS.** Entire file is `await file.read()` before the size check; no ASGI request‑size cap; no rate limiting (`cases.py:69`, `case_service.py:104`). *Remediation:* streaming size guard + ASGI body limit + rate limiting.
6. **No real file‑type enforcement.** No MIME/extension allowlist; magic bytes checked only for declared PDFs; all else falls through to text parsing with a client‑controlled `content_type` (`validators.py:18-19`, `pipeline.py:28-39`). *Remediation:* server‑side content sniffing + explicit allowlist.
7. **Parser resource/error handling.** PyPDF2 has no page/size cap and a bare `except: pass` that hides malformed input (`pdf_parser.py:25-27`); `flatten_dict` recurses unboundedly on nested JSON (`json_parser.py:18-19`). *Remediation:* page/depth caps, explicit error surfacing, decompression‑bomb guards.
8. **PII may leak into logs via exception strings.** `error=str(exc)` in catch‑alls can embed evidence fragments (`app.py:52,107`, `case_service.py:135`); no structlog redaction processor (`logger.py:10-18`). *Remediation:* redaction processor + structured, content‑free error logging.
9. **Grounding is substring‑presence, not semantic** (`claim_verifier.py:26-37, 58-69`). *Remediation:* minimum‑specificity rules per fact type and requirement‑to‑fact binding so the *relevant* fact must ground.

### LOW
10. **Unsanitized filename stored, echoed, and logged** (`cases.py:74`, `repositories.py:140`, returned at `cases.py:58-59`, logged at `case_service.py:117`) — stored‑XSS/UI‑injection risk on the frontend surface. *Remediation:* sanitize/normalize filenames on intake.
11. **Permissive CORS methods/headers** with `allow_credentials=True` (`app.py:83-85`) — dev‑only origins, moot for non‑browser clients given #1.
12. **No security headers / HTTPS enforcement / TrustedHost; audit log lacks actor attribution** (`migrations.py:166-179`) — cannot attribute *who* acted, only *what* stage ran.

---

## 8. Planned hardening pass

Items #3 (remove dead code), #10 (filename sanitization), #5/#7 (upload/parse resource guards), and #8 (log redaction) are **non‑breaking** and compatible with the frozen evaluation and API contract; they are the intended next hardening batch, each to be landed with a regression test and a full `pytest` + contract‑check + evaluation re‑run to prove no behavioral drift. Items #1, #2, #6, #11, #12 are production‑deployment concerns tracked here as explicit, accepted, documented risk for the prototype.

---

*Honesty note: this register is deliberately unsoftened. A system whose entire thesis is "never overstate what the evidence supports" must hold its own security claims to the same bar.*
