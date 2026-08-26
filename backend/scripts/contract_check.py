#!/usr/bin/env python3
"""In-process frontend/backend contract verifier.

Boots the real DisputeShield ASGI app with Starlette's ``TestClient`` (no socket
bind, so it runs anywhere), loads the five canonical demo cases, and walks every
endpoint the frontend actually calls (``frontend/src/lib/api.ts``) for each case.
Every payload is validated field-by-field against the TypeScript wire contract
(``frontend/src/lib/types.ts``): required keys present, JSON types correct, every
enum-valued field within its declared union, nullability respected.

This is the verification the passing ``vite build`` cannot give: the compiler
proves the frontend only *reads* fields declared in ``types.ts``; this proves the
backend actually *emits* those fields, with those types, for every archetype —
including the empty/null shapes (sparse E, abstaining B) that crash UIs when a
field the code assumes is present arrives ``null`` or missing.

Exit code is non-zero if any CONTRACT error is found. Archetype behavioral
expectations (from ``demo.py``) are reported and flagged but do not, on their
own, fail the run — they describe engine behavior, not the wire contract.

Run from the backend dir:  ./venv/bin/python scripts/contract_check.py
"""

from __future__ import annotations

import enum
import os
import sys
import tempfile
from typing import Any, Callable, Dict, List, Optional

# Ensure the backend package root (parent of this scripts/ dir) is importable
# whether run as `scripts/contract_check.py` or from elsewhere.
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

# Point every DB operation at a throwaway file so this verifier never mutates the
# real development database and is fully reproducible. This MUST be set before
# any `src.database` import binds DB_PATH as a default argument.
_TMP_DB_DIR = tempfile.mkdtemp(prefix="ds_contract_")
os.environ["DISPUTESHIELD_DB"] = os.path.join(_TMP_DB_DIR, "contract_check.db")

# ---------------------------------------------------------------------------
# TypeScript union transcriptions (frontend/src/lib/types.ts). These are the
# source of truth the compiler enforced on the frontend; we assert the backend
# agrees with them.
# ---------------------------------------------------------------------------
TS_UNIONS: Dict[str, set] = {
    "CardNetwork": {"VISA", "MASTERCARD"},
    "DisputeCategory": {"FRAUD_UNAUTHORIZED"},
    "DisputePhase": {"FRAUD", "RETRIEVAL", "CHARGEBACK", "PRE_ARBITRATION", "ARBITRATION"},
    "CaseStatus": {
        "OPEN", "INGESTING", "ANALYZING", "REVIEW_REQUIRED", "PACKAGE_READY",
        "SUBMITTED", "WON", "LOST", "CLOSED",
    },
    "EvidenceSourceType": {
        "ACCESS_LOG", "SERVER_LOG", "EMAIL", "INVOICE", "SCREENSHOT", "CSV_LOG",
        "JSON_LOG", "PDF_DOCUMENT", "SUPPORT_CHAT", "PAYMENT_RECORD",
        "TERMS_OF_SERVICE", "AUTHENTICATION_LOG", "DEVICE_LOG", "DOWNLOAD_LOG",
        "HISTORICAL_TRANSACTION", "OTHER",
    },
    "EvidenceType": {
        "PAYMENT_PROOF", "IDENTITY_PROOF", "ACCESS_PROOF", "DELIVERY_PROOF",
        "AUTHENTICATION_PROOF", "COMMUNICATION", "POLICY_DOCUMENT",
        "USAGE_METRICS", "HISTORICAL_MATCH",
    },
    "FactType": {
        "IP_ADDRESS", "DEVICE_ID", "DEVICE_FINGERPRINT", "EMAIL_ADDRESS",
        "TIMESTAMP", "CUSTOMER_NAME", "ACCOUNT_ID", "PAYMENT_ID", "ORDER_ID",
        "AMOUNT", "CURRENCY", "USER_AGENT", "GEO_LOCATION", "SESSION_ID",
        "DOWNLOAD_HASH", "LICENSE_KEY", "ECI_VALUE", "CAVV", "DS_TRANS_ID",
        "AVS_RESULT", "CVV_RESULT", "ACTION_DESCRIPTION", "PRODUCT_NAME",
        "REFUND_AMOUNT", "OTHER",
    },
    "RequirementStatus": {
        "SATISFIED", "PARTIALLY_SATISFIED", "MISSING", "CONTRADICTED",
        "NOT_APPLICABLE",
    },
    "RequirementStrength": {"REQUIRED", "STRONG", "SUPPORTING"},
    "ClaimStatus": {"VERIFIED", "BLOCKED", "NEEDS_REVIEW", "DRAFT"},
    "Recommendation": {"CONTEST", "REVIEW", "INSUFFICIENT", "ABSTAIN"},
    "TimelineAnomalyType": {
        "IMPOSSIBLE_ORDER", "SUSPICIOUS_GAP", "DUPLICATE_EVENT",
        "FUTURE_TIMESTAMP", "MISSING_EXPECTED_EVENT",
    },
    "ExtractionMethod": {"DETERMINISTIC", "REGEX", "LLM", "OCR"},
    "ScoringFactorType": {"POSITIVE", "NEGATIVE", "MISSING"},
    "ContradictionType": {
        "IP_MISMATCH", "IDENTITY_MISMATCH", "AMOUNT_MISMATCH", "TIMELINE_ORDER",
        "USAGE_BEFORE_PURCHASE", "CUSTOMER_STATEMENT_CONFLICT", "FUTURE_TIMESTAMP",
    },
    "GateStatus": {"MANDATORY_REVIEW", "READY", "NEEDS_REVIEW", "NOT_RECOMMENDED"},
    "Severity": {"LOW", "MEDIUM", "HIGH"},
}

errors: List[str] = []       # contract violations -> fail
warnings: List[str] = []     # drift / informational -> report only


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


# ---------------------------------------------------------------------------
# Part 1 — enum parity between backend enums and the TS unions.
# ---------------------------------------------------------------------------
def check_enum_parity() -> None:
    print("\n=== Part 1: enum parity (backend enums  vs  types.ts unions) ===")
    modules = []
    for modname in ("src.domain.enums",):
        try:
            modules.append(__import__(modname, fromlist=["*"]))
        except Exception as exc:  # pragma: no cover - import guard
            err(f"could not import {modname}: {exc!r}")
            return
    # optional homes for gate/severity enums
    for modname in ("src.orchestrator.gate", "src.domain.models"):
        try:
            modules.append(__import__(modname, fromlist=["*"]))
        except Exception:
            pass

    found: Dict[str, set] = {}
    for mod in modules:
        for name in dir(mod):
            obj = getattr(mod, name)
            if isinstance(obj, type) and issubclass(obj, enum.Enum) and obj is not enum.Enum:
                try:
                    values = {m.value for m in obj}
                except Exception:
                    continue
                # only string-valued enums map to TS string unions
                if all(isinstance(v, str) for v in values):
                    found.setdefault(obj.__name__, values)

    checked = 0
    for ts_name, ts_values in TS_UNIONS.items():
        if ts_name not in found:
            warn(f"enum {ts_name}: no matching backend enum class found (declared as plain string?)")
            continue
        checked += 1
        be_values = found[ts_name]
        missing_in_ts = be_values - ts_values      # backend can emit, TS doesn't know -> real risk
        extra_in_ts = ts_values - be_values         # TS knows, backend never emits -> harmless
        if missing_in_ts:
            err(f"enum {ts_name}: backend emits values MISSING from types.ts union: {sorted(missing_in_ts)}")
        if extra_in_ts:
            warn(f"enum {ts_name}: types.ts declares values the backend enum lacks (harmless): {sorted(extra_in_ts)}")
        if not missing_in_ts and not extra_in_ts:
            print(f"  ok  {ts_name:<22} {len(be_values)} values match exactly")
    print(f"  checked {checked} enums against the backend")


# ---------------------------------------------------------------------------
# Part 2 — a tiny schema DSL mirroring types.ts, and the validators.
# ---------------------------------------------------------------------------
Validator = Callable[[Any, str], None]


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def v_str(nullable: bool = False) -> Validator:
    def f(v: Any, path: str) -> None:
        if v is None:
            if not nullable:
                err(f"{path}: expected string, got null")
            return
        if not isinstance(v, str):
            err(f"{path}: expected string, got {type(v).__name__}")
    return f


def v_num(nullable: bool = False) -> Validator:
    def f(v: Any, path: str) -> None:
        if v is None:
            if not nullable:
                err(f"{path}: expected number, got null")
            return
        if not _is_num(v):
            err(f"{path}: expected number, got {type(v).__name__}")
    return f


def v_bool(v: Any, path: str) -> None:
    if not isinstance(v, bool):
        err(f"{path}: expected bool, got {type(v).__name__} ({v!r})")


def v_enum(union: str, nullable: bool = False) -> Validator:
    allowed = TS_UNIONS[union]

    def f(v: Any, path: str) -> None:
        if v is None:
            if not nullable:
                err(f"{path}: expected {union}, got null")
            return
        if not isinstance(v, str):
            err(f"{path}: expected {union} string, got {type(v).__name__}")
            return
        if v not in allowed:
            err(f"{path}: value {v!r} not in {union} union {sorted(allowed)}")
    return f


def v_enumish(union: str, nullable: bool = False) -> Validator:
    """types.ts types this field as plain `string` but the backend uses an enum;
    validate as string, and report (warn only) if the value escapes the union
    the status helpers switch on."""
    allowed = TS_UNIONS[union]

    def f(v: Any, path: str) -> None:
        if v is None:
            if not nullable:
                err(f"{path}: expected string, got null")
            return
        if not isinstance(v, str):
            err(f"{path}: expected string, got {type(v).__name__}")
            return
        if v not in allowed:
            warn(f"{path}: {v!r} outside known {union} set {sorted(allowed)} (UI intent falls back to default)")
    return f


def v_dict(nullable: bool = False) -> Validator:
    def f(v: Any, path: str) -> None:
        if v is None:
            if not nullable:
                err(f"{path}: expected object, got null")
            return
        if not isinstance(v, dict):
            err(f"{path}: expected object, got {type(v).__name__}")
    return f


def v_arr(elem: Validator) -> Validator:
    def f(v: Any, path: str) -> None:
        if not isinstance(v, list):
            err(f"{path}: expected array, got {type(v).__name__}")
            return
        for i, item in enumerate(v):
            elem(item, f"{path}[{i}]")
    return f


def v_obj(fields: Dict[str, Validator], nullable: bool = False) -> Validator:
    def f(v: Any, path: str) -> None:
        if v is None:
            if not nullable:
                err(f"{path}: expected object, got null")
            return
        if not isinstance(v, dict):
            err(f"{path}: expected object, got {type(v).__name__}")
            return
        for key, val in fields.items():
            if key not in v:
                err(f"{path}.{key}: MISSING required key")
            else:
                val(v[key], f"{path}.{key}")
        for extra in set(v) - set(fields):
            warn(f"{path}.{extra}: extra key not in types.ts (harmless to TS, possible drift)")
    return f


# ---- schemas mirroring types.ts interfaces ------------------------------
PROVENANCE = v_obj({
    "source_file": v_str(), "source_location": v_str(), "content_hash": v_str(),
})
EXTRACTED_FACT = v_obj({
    "type": v_enum("FactType"), "value": v_str(), "confidence": v_num(),
    "extraction_method": v_enum("ExtractionMethod"), "provenance": PROVENANCE,
})
EVIDENCE_ITEM = v_obj({
    "id": v_str(), "case_id": v_str(), "source_type": v_enum("EvidenceSourceType"),
    "semantic_type": v_enum("EvidenceType"), "file_path": v_str(nullable=True),
    "raw_content": v_str(nullable=True), "extracted_facts": v_arr(EXTRACTED_FACT),
    "confidence": v_num(), "created_at": v_str(),
})
TIMELINE_ANOMALY = v_obj({
    "type": v_enum("TimelineAnomalyType"), "description": v_str(),
    "severity": v_enumish("Severity"),
})
TIMELINE_EVENT = v_obj({
    "id": v_str(), "timestamp": v_str(), "description": v_str(),
    "evidence_id": v_str(), "event_type": v_str(nullable=True),
    "actor": v_str(nullable=True), "ip_address": v_str(nullable=True),
    "anomalies": v_arr(TIMELINE_ANOMALY),
})
CLAIM = v_obj({
    "id": v_str(), "description": v_str(), "status": v_enum("ClaimStatus"),
    "supporting_evidence_ids": v_arr(v_str()), "block_reason": v_str(nullable=True),
})
REQUIREMENT = v_obj({
    "id": v_str(), "name": v_str(), "description": v_str(),
    "status": v_enum("RequirementStatus"), "strength": v_enumish("RequirementStrength"),
    "coverage": v_num(), "is_auto_win": v_bool, "evidence_candidates": v_arr(v_str()),
    "satisfied_fact_types": v_arr(v_str()), "missing_fact_types": v_arr(v_str()),
    "source_reference": v_str(),
})
CONTRADICTION = v_obj({
    "claim_a_id": v_str(nullable=True), "claim_b_id": v_str(nullable=True),
    "evidence_a_id": v_str(nullable=True), "evidence_b_id": v_str(nullable=True),
    "description": v_str(), "severity": v_enumish("Severity"),
    "type": v_enumish("ContradictionType"),
})
SCORING_FACTOR = v_obj({
    "name": v_str(), "type": v_enum("ScoringFactorType"), "points": v_num(),
    "description": v_str(), "evidence_ids": v_arr(v_str()),
})
EVIDENCE_SCORE = v_obj({
    "total_score": v_num(), "factors": v_arr(SCORING_FACTOR),
    "recommendation": v_enum("Recommendation"),
})
QUALIFYING_TX = v_obj({
    "evidence_id": v_str(), "days_before_dispute": v_num(),
    "matching_elements": v_arr(v_str()),
})
CE30 = v_obj({
    "qualified": v_bool, "matching_elements": v_arr(v_str()),
    "qualifying_transactions": v_arr(v_str()),
    "qualifying_details": v_arr(QUALIFYING_TX), "reason": v_str(),
})
EVIDENCE_PACKAGE = v_obj({
    "case_id": v_str(), "claims": v_arr(CLAIM), "requirements": v_arr(REQUIREMENT),
    "score": v_obj({  # nullable EvidenceScore
        "total_score": v_num(), "factors": v_arr(SCORING_FACTOR),
        "recommendation": v_enum("Recommendation"),
    }, nullable=True),
    "timeline": v_arr(TIMELINE_EVENT), "contradictions": v_arr(CONTRADICTION),
    "recommendation": v_enum("Recommendation", nullable=True),
    "review_required": v_bool, "review_reasons": v_arr(v_str()),
    "network_submission": v_dict(nullable=True), "generated_at": v_str(),
})
DISPUTE_CASE = v_obj({
    "id": v_str(), "merchant_id": v_str(), "transaction_id": v_str(),
    "dispute_id": v_str(nullable=True), "amount": v_num(), "currency": v_str(),
    "network": v_enum("CardNetwork"), "category": v_enum("DisputeCategory"),
    "reason_code": v_str(), "phase": v_enum("DisputePhase"),
    "status": v_enum("CaseStatus"), "transaction_date": v_str(nullable=True),
    "respond_by": v_str(nullable=True), "created_at": v_str(), "updated_at": v_str(),
    "evidence_items": v_arr(EVIDENCE_ITEM), "claims": v_arr(CLAIM),
    "package": EVIDENCE_PACKAGE,  # declared EvidencePackage | null
})
# `package` is nullable on the wire; wrap to allow null.
DISPUTE_CASE = v_obj({
    "id": v_str(), "merchant_id": v_str(), "transaction_id": v_str(),
    "dispute_id": v_str(nullable=True), "amount": v_num(), "currency": v_str(),
    "network": v_enum("CardNetwork"), "category": v_enum("DisputeCategory"),
    "reason_code": v_str(), "phase": v_enum("DisputePhase"),
    "status": v_enum("CaseStatus"), "transaction_date": v_str(nullable=True),
    "respond_by": v_str(nullable=True), "created_at": v_str(), "updated_at": v_str(),
    "evidence_items": v_arr(EVIDENCE_ITEM), "claims": v_arr(CLAIM),
    "package": lambda v, p: (None if v is None else EVIDENCE_PACKAGE(v, p)),
})
CASE_ANALYSIS = v_obj({
    "case_id": v_str(), "status": v_enum("CaseStatus"), "score": EVIDENCE_SCORE,
    "recommendation": v_enum("Recommendation"), "gate_status": v_enum("GateStatus"),
    "gate_reasons": v_arr(v_str()), "requirements": v_arr(REQUIREMENT),
    "claims": v_arr(CLAIM), "contradictions": v_arr(CONTRADICTION),
    "timeline": v_arr(TIMELINE_EVENT),
    "ce30": lambda v, p: (None if v is None else CE30(v, p)),
    "injection_detected": v_bool, "injection_patterns": v_arr(v_str()),
})
AUDIT_LOG_ENTRY = v_obj({
    "id": v_str(), "case_id": v_str(), "timestamp": v_str(),
    "pipeline_stage": v_str(), "model_used": v_str(),
    "prompt_hash": v_str(nullable=True), "decision": v_str(),
    "confidence": v_num(), "latency_ms": v_num(),
})


# ---------------------------------------------------------------------------
# Part 2/3 driver — walk the real API and validate + behavioral report.
# ---------------------------------------------------------------------------
DEMO_EXPECT = {
    "A": dict(net="VISA", rc="10.4", rec={"CONTEST"}, gate={"READY"},
              injection=False, contradictions="0", note="strong: 3DS auto-win"),
    "B": dict(net="MASTERCARD", rc="4837", rec={"ABSTAIN", "INSUFFICIENT"},
              gate={"NOT_RECOMMENDED"}, injection=False, contradictions="0",
              note="insufficient: invoice only"),
    "C": dict(net="VISA", rc="10.4", rec=None, gate={"MANDATORY_REVIEW"},
              injection=False, contradictions="1+", note="contradictory: IP + denial"),
    "D": dict(net="MASTERCARD", rc="4837", rec=None, gate={"MANDATORY_REVIEW"},
              injection=True, contradictions="*", note="prompt injection"),
    "E": dict(net="VISA", rc="10.4", rec={"ABSTAIN", "INSUFFICIENT"}, gate=None,
              injection=False, contradictions="*", note="sparse: single note"),
}


def check_count(spec: str, n: int) -> str:
    if spec == "*":
        return "·"
    if spec == "0":
        return "PASS" if n == 0 else "FLAG"
    if spec == "1+":
        return "PASS" if n >= 1 else "FLAG"
    return "?"


def run_api_checks() -> None:
    from fastapi.testclient import TestClient
    import src.api.app as appmod

    print("\n=== Part 2: live wire-contract validation via in-process TestClient ===")
    with TestClient(appmod.app) as client:
        # 1) demo/load
        r = client.post("/api/demo/load")
        if r.status_code != 200:
            err(f"POST /api/demo/load -> {r.status_code}: {r.text[:200]}")
            return
        demo = r.json()
        for k in ("status", "created_cases", "count"):
            if k not in demo:
                err(f"demo/load response missing key {k!r} (DemoLoadResponse)")
        ids = demo.get("created_cases", [])
        print(f"  demo/load: status={demo.get('status')!r} count={demo.get('count')} ids={len(ids)}")
        if len(ids) != 5:
            warn(f"expected 5 demo cases, got {len(ids)}")

        # 2) list
        r = client.get("/api/cases/")
        if r.status_code != 200:
            err(f"GET /api/cases/ -> {r.status_code}")
        else:
            lst = r.json()
            if not isinstance(lst, list):
                err("GET /api/cases/ did not return an array")
            else:
                for i, c in enumerate(lst):
                    DISPUTE_CASE(c, f"list[{i}]")
                print(f"  GET /api/cases/ : {len(lst)} cases, validated as DisputeCase[]")

        # 3) per-case full walk
        letters = ["A", "B", "C", "D", "E"]
        print("\n  per-case endpoint walk + behavioral report:")
        print("  " + "-" * 96)
        print(f"  {'demo':<5}{'net/rc':<16}{'recommendation':<15}{'gate':<18}"
              f"{'score':<7}{'req(sat)':<10}{'contra':<8}{'inj':<5}{'ce30':<6}")
        print("  " + "-" * 96)
        for idx, cid in enumerate(ids):
            letter = letters[idx] if idx < len(letters) else f"#{idx}"
            exp = DEMO_EXPECT.get(letter, {})

            rc_case = client.get(f"/api/cases/{cid}")
            rc_an = client.get(f"/api/cases/{cid}/analysis")
            rc_pk = client.get(f"/api/cases/{cid}/package")
            rc_au = client.get(f"/api/cases/{cid}/audit")
            rc_tl = client.get(f"/api/cases/{cid}/timeline")

            for label, resp, validator, is_list in [
                (f"GET /cases/{cid}", rc_case, DISPUTE_CASE, False),
                (f"GET /cases/{cid}/analysis", rc_an, CASE_ANALYSIS, False),
                (f"GET /cases/{cid}/package", rc_pk, EVIDENCE_PACKAGE, False),
                (f"GET /cases/{cid}/audit", rc_au, AUDIT_LOG_ENTRY, True),
                (f"GET /cases/{cid}/timeline", rc_tl, TIMELINE_EVENT, True),
            ]:
                if resp.status_code != 200:
                    err(f"{label} -> {resp.status_code}: {resp.text[:160]}")
                    continue
                body = resp.json()
                if is_list:
                    if not isinstance(body, list):
                        err(f"{label}: expected array")
                    else:
                        for i, item in enumerate(body):
                            validator(item, f"{letter}:{label}[{i}]")
                else:
                    validator(body, f"{letter}:{label}")

            # behavioral snapshot from the analysis + package
            an = rc_an.json() if rc_an.status_code == 200 else {}
            case = rc_case.json() if rc_case.status_code == 200 else {}
            score = (an.get("score") or {}).get("total_score")
            rec = an.get("recommendation")
            gate = an.get("gate_status")
            reqs = an.get("requirements") or []
            sat = sum(1 for q in reqs if q.get("status") == "SATISFIED")
            contra = an.get("contradictions") or []
            inj = an.get("injection_detected")
            ce30 = an.get("ce30")
            ce30s = "-" if ce30 is None else ("Y" if ce30.get("qualified") else "N")
            netrc = f"{case.get('network','?')[:4]}/{case.get('reason_code','?')}"
            print(f"  {letter:<5}{netrc:<16}{str(rec):<15}{str(gate):<18}"
                  f"{str(score):<7}{f'{len(reqs)}({sat})':<10}"
                  f"{f'{len(contra)}':<8}{str(inj):<5}{ce30s:<6}")

            # behavioral flags (reported, not fatal)
            if exp:
                if exp.get("net") and case.get("network") != exp["net"]:
                    warn(f"{letter}: network {case.get('network')} != expected {exp['net']}")
                if exp.get("rc") and case.get("reason_code") != exp["rc"]:
                    warn(f"{letter}: reason_code {case.get('reason_code')} != expected {exp['rc']}")
                if exp.get("rec") and rec not in exp["rec"]:
                    warn(f"{letter}: recommendation {rec!r} not in expected {exp['rec']} ({exp['note']})")
                if exp.get("gate") and gate not in exp["gate"]:
                    warn(f"{letter}: gate {gate!r} not in expected {exp['gate']} ({exp['note']})")
                if exp.get("injection") is not None and bool(inj) != exp["injection"]:
                    warn(f"{letter}: injection_detected {inj} != expected {exp['injection']} ({exp['note']})")
                cflag = check_count(exp.get("contradictions", "*"), len(contra))
                if cflag == "FLAG":
                    warn(f"{letter}: contradictions={len(contra)} violates expectation "
                         f"{exp['contradictions']!r} ({exp['note']})")
        print("  " + "-" * 96)

        # 4) manual create + analyze (NewCaseModal happy path; empty-evidence edge)
        print("\n=== Part 3: manual create + analyze (empty-evidence edge case) ===")
        body = {
            "merchant_id": "merchant_manual",
            "transaction_id": "tx_manual_0001",
            "amount": 1000.0,
            "currency": "INR",
            "network": "VISA",
            "reason_code": "10.4",
        }
        rc = client.post("/api/cases/", json=body)
        if rc.status_code != 200:
            err(f"POST /api/cases/ (manual) -> {rc.status_code}: {rc.text[:200]}")
        else:
            created = rc.json()
            DISPUTE_CASE(created, "manual:create")
            mid = created["id"]
            ra = client.get(f"/api/cases/{mid}/analysis")
            if ra.status_code != 200:
                err(f"manual analysis -> {ra.status_code}: {ra.text[:200]}")
            else:
                CASE_ANALYSIS(ra.json(), "manual:analysis")
                a = ra.json()
                print(f"  manual case with NO evidence: rec={a.get('recommendation')!r} "
                      f"gate={a.get('gate_status')!r} reqs={len(a.get('requirements') or [])} "
                      f"score={(a.get('score') or {}).get('total_score')} "
                      f"claims={len(a.get('claims') or [])}  (must not crash; expect abstain-ish)")
            rp = client.get(f"/api/cases/{mid}/package")
            if rp.status_code != 200:
                err(f"manual package -> {rp.status_code}: {rp.text[:200]}")
            else:
                EVIDENCE_PACKAGE(rp.json(), "manual:package")


def main() -> int:
    print(f"(using throwaway database: {os.environ['DISPUTESHIELD_DB']})")
    check_enum_parity()
    run_api_checks()

    print("\n=== Summary ===")
    if warnings:
        print(f"\n  {len(warnings)} warning(s) / informational:")
        for w in warnings:
            print(f"    ~ {w}")
    if errors:
        print(f"\n  {len(errors)} CONTRACT ERROR(S):")
        for e in errors:
            print(f"    ✗ {e}")
        print("\n  RESULT: CONTRACT MISMATCH — frontend would receive data it does not expect.")
        return 1
    print("\n  RESULT: OK — every endpoint payload for all archetypes conforms to types.ts.")
    print("  (Warnings above, if any, are non-fatal drift/behavioral notes.)")
    return 0


if __name__ == "__main__":
    import shutil

    try:
        code = main()
    finally:
        shutil.rmtree(_TMP_DB_DIR, ignore_errors=True)
    sys.exit(code)
