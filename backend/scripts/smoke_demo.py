"""End-to-end smoke test of the real backend stack against the five demo cases.

Not a unit test: this drives service -> repositories -> sqlite -> verification ->
scoring -> gate exactly as the running app would, then asserts each canonical
case lands on its designed decision path. Run:

    PYTHONPATH="$PWD/backend" backend/venv/bin/python scripts/smoke_demo.py
"""

import asyncio
import os
import sys
import tempfile

# Ensure `src` is importable when run directly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from src.api.routes.demo import _DEMO_CASES, _dt
from src.database.migrations import init_db
from src.database.repositories import (
    AuditRepository,
    CaseRepository,
    ClaimRepository,
    EvidenceRepository,
    TimelineRepository,
)
from src.domain.enums import Recommendation
from src.domain.models import CaseCreateRequest
from src.extraction.llm_client import MockLLMClient
from src.orchestrator.case_service import CaseService
from src.orchestrator.gate import GateStatus

# (recommendation, gate_status, expect_contradictions, expect_injection)
EXPECTED = {
    "A": (Recommendation.CONTEST, GateStatus.READY, False, False),
    "B": (Recommendation.ABSTAIN, GateStatus.NOT_RECOMMENDED, False, False),
    "C": (Recommendation.REVIEW, GateStatus.MANDATORY_REVIEW, True, False),
    "D": (Recommendation.REVIEW, GateStatus.MANDATORY_REVIEW, False, True),
    "E": (Recommendation.ABSTAIN, GateStatus.NOT_RECOMMENDED, False, False),
}


async def main() -> int:
    tmp = tempfile.mkdtemp(prefix="disputeshield_smoke_")
    db_path = os.path.join(tmp, "smoke.db")
    await init_db(db_path)

    service = CaseService(
        case_repo=CaseRepository(db_path=db_path),
        evidence_repo=EvidenceRepository(db_path=db_path),
        claim_repo=ClaimRepository(db_path=db_path),
        timeline_repo=TimelineRepository(db_path=db_path),
        audit_repo=AuditRepository(db_path=db_path),
        llm_client=MockLLMClient(),
    )

    failures = []
    reload_target = None  # (letter, case_id) of a strong case to round-trip
    print(f"{'Case':<44} {'Recommendation':<14} {'Gate':<18} {'Contra':<7} {'Inject':<7} {'CE30':<6} Result")
    print("-" * 110)

    for i, (meta, builder) in enumerate(_DEMO_CASES):
        letter = meta["desc"][0]
        req = CaseCreateRequest(
            merchant_id="merchant_demo",
            transaction_id=f"tx_demo_{i + 1:04d}",
            amount=meta["amount"],
            currency="INR",
            network=meta["network"],
            reason_code=meta["reason_code"],
            transaction_date=_dt(meta["txn_date"]),
        )
        case = await service.create_case(req)
        for ev in builder(case.id):
            await service.evidence_repo.create_evidence(ev)

        analysis = await service.analyze_case(case.id)
        rec = analysis.score.recommendation
        gate = analysis.gate_result.gate_status
        n_contra = len(analysis.contradictions)
        inj = analysis.injection_detected
        ce30_ok = bool(analysis.ce30_result and analysis.ce30_result.qualified)

        if letter == "A":
            await service.generate_package(case.id)
            reload_target = (letter, case.id, len(analysis.claims), len(analysis.timeline))

        exp_rec, exp_gate, exp_contra, exp_inj = EXPECTED[letter]
        ok = (
            rec == exp_rec
            and gate == exp_gate
            and (n_contra > 0) == exp_contra
            and inj == exp_inj
        )
        if not ok:
            failures.append(
                f"{meta['desc']}: got rec={rec.value} gate={gate.value} contra={n_contra} inj={inj}; "
                f"expected rec={exp_rec.value} gate={exp_gate.value} contra={exp_contra} inj={exp_inj}"
            )
        print(
            f"{meta['desc']:<44} {rec.value:<14} {gate.value:<18} "
            f"{n_contra:<7} {str(inj):<7} {str(ce30_ok):<6} {'PASS' if ok else 'FAIL'}"
        )

    print("-" * 110)

    # Persistence round-trip: reload a strong case from a *fresh* service bound to
    # the same file and confirm the rewritten read paths reconstruct everything.
    if reload_target:
        letter, case_id, n_claims, n_events = reload_target
        fresh = CaseService(
            case_repo=CaseRepository(db_path=db_path),
            evidence_repo=EvidenceRepository(db_path=db_path),
            claim_repo=ClaimRepository(db_path=db_path),
            timeline_repo=TimelineRepository(db_path=db_path),
            audit_repo=AuditRepository(db_path=db_path),
            llm_client=MockLLMClient(),
        )
        reloaded = await fresh.case_repo.get_case(case_id)
        r_evidence = await fresh.evidence_repo.get_evidence_by_case(case_id)
        r_claims = await fresh.claim_repo.get_claims_by_case(case_id)
        r_timeline = await fresh.timeline_repo.get_timeline_by_case(case_id)
        prov_ok = any(
            f.provenance and f.provenance.content_hash
            for e in r_evidence for f in e.extracted_facts
        )
        checks = {
            "case reloads": reloaded is not None,
            "package persisted": bool(reloaded and reloaded.package),
            "evidence reloads": len(r_evidence) > 0,
            "provenance hashes reload": prov_ok,
            "claims persisted": len(r_claims) == n_claims and n_claims > 0,
            "timeline persisted": len(r_timeline) == n_events and n_events > 0,
        }
        print(f"Persistence round-trip (case {letter} = {case_id}):")
        for name, passed in checks.items():
            print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
            if not passed:
                failures.append(f"round-trip: {name}")
        print("-" * 110)

    if failures:
        print(f"\n{len(failures)} FAILURE(S):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nAll five demo cases landed on their designed decision paths.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
