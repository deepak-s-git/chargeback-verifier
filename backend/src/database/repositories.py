"""Data-access layer.

Each repository owns a database *path*, not a live connection, and opens a
short-lived connection per operation via :func:`get_db_connection`. This keeps
the previous ``create_*`` write methods, fills in the previously-stubbed read
methods (which returned ``[]``/``None`` and silently broke every GET endpoint
and any case reload), and adds ``delete_*_by_case`` so re-running analysis is
idempotent rather than appending duplicate rows.

Reconstruction is faithful: evidence is rehydrated with its full provenance-
bearing facts, claims with their supporting-evidence ids, and timeline events
with their enriched semantic fields and anomalies — so a reloaded case verifies
identically to a freshly-analysed one.
"""

import json
from typing import List, Optional

from src.database.db import DB_PATH, get_db_connection
from src.domain.enums import (
    ClaimStatus,
    EvidenceSourceType,
    EvidenceType,
    ExtractionMethod,
    FactType,
)
from src.domain.models import (
    AuditLogEntry,
    Claim,
    DisputeCase,
    EvidenceItem,
    EvidencePackage,
    ExtractedFact,
    Provenance,
    TimelineAnomaly,
    TimelineEvent,
)


class CaseRepository:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    async def create_case(self, case: DisputeCase) -> DisputeCase:
        query = """
            INSERT INTO cases (
                id, merchant_id, transaction_id, dispute_id, amount, currency,
                network, category, reason_code, phase, status,
                transaction_date, respond_by, created_at, updated_at, package_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        async with get_db_connection(self.db_path) as db:
            await db.execute(
                query,
                (
                    case.id, case.merchant_id, case.transaction_id, case.dispute_id,
                    case.amount, case.currency, case.network.value, case.category.value,
                    case.reason_code, case.phase.value, case.status.value,
                    case.transaction_date.isoformat() if case.transaction_date else None,
                    case.respond_by.isoformat() if case.respond_by else None,
                    case.created_at.isoformat(), case.updated_at.isoformat(),
                    case.package.model_dump_json() if case.package else None,
                ),
            )
            await db.commit()
        return case

    def _row_to_case(self, row) -> DisputeCase:
        package = None
        if row["package_data"]:
            package = EvidencePackage.model_validate_json(row["package_data"])
        return DisputeCase(
            id=row["id"],
            merchant_id=row["merchant_id"],
            transaction_id=row["transaction_id"],
            dispute_id=row["dispute_id"],
            amount=row["amount"],
            currency=row["currency"],
            network=row["network"],
            category=row["category"],
            reason_code=row["reason_code"],
            phase=row["phase"],
            status=row["status"],
            transaction_date=row["transaction_date"],
            respond_by=row["respond_by"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            package=package,
        )

    async def get_case(self, case_id: str) -> Optional[DisputeCase]:
        async with get_db_connection(self.db_path) as db:
            async with db.execute("SELECT * FROM cases WHERE id = ?", (case_id,)) as cursor:
                row = await cursor.fetchone()
                return self._row_to_case(row) if row else None

    async def update_case(self, case: DisputeCase) -> DisputeCase:
        query = """
            UPDATE cases SET
                phase = ?, status = ?, transaction_date = ?, respond_by = ?,
                updated_at = ?, package_data = ?
            WHERE id = ?
        """
        async with get_db_connection(self.db_path) as db:
            await db.execute(
                query,
                (
                    case.phase.value, case.status.value,
                    case.transaction_date.isoformat() if case.transaction_date else None,
                    case.respond_by.isoformat() if case.respond_by else None,
                    case.updated_at.isoformat(),
                    case.package.model_dump_json() if case.package else None,
                    case.id,
                ),
            )
            await db.commit()
        return case

    async def list_cases(self) -> List[DisputeCase]:
        async with get_db_connection(self.db_path) as db:
            async with db.execute("SELECT * FROM cases ORDER BY created_at DESC") as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_case(row) for row in rows]


class EvidenceRepository:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    async def create_evidence(self, evidence: EvidenceItem) -> EvidenceItem:
        async with get_db_connection(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO evidence_items (
                    id, case_id, source_type, semantic_type, file_path,
                    raw_content, confidence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence.id, evidence.case_id, evidence.source_type.value,
                    evidence.semantic_type.value, evidence.file_path, evidence.raw_content,
                    evidence.confidence, evidence.created_at.isoformat(),
                ),
            )
            for fact in evidence.extracted_facts:
                await db.execute(
                    """
                    INSERT INTO extracted_facts (
                        evidence_id, type, value, confidence, extraction_method,
                        source_file, source_location, content_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        evidence.id, fact.type.value, fact.value, fact.confidence,
                        fact.extraction_method.value, fact.provenance.source_file,
                        fact.provenance.source_location, fact.provenance.content_hash,
                    ),
                )
            await db.commit()
        return evidence

    async def _facts_for(self, db, evidence_id: str) -> List[ExtractedFact]:
        facts: List[ExtractedFact] = []
        async with db.execute(
            "SELECT * FROM extracted_facts WHERE evidence_id = ? ORDER BY id", (evidence_id,)
        ) as cursor:
            async for f in cursor:
                facts.append(
                    ExtractedFact(
                        type=FactType(f["type"]),
                        value=f["value"],
                        confidence=f["confidence"],
                        extraction_method=ExtractionMethod(f["extraction_method"]),
                        provenance=Provenance(
                            source_file=f["source_file"],
                            source_location=f["source_location"],
                            content_hash=f["content_hash"],
                        ),
                    )
                )
        return facts

    def _row_to_evidence(self, row, facts: List[ExtractedFact]) -> EvidenceItem:
        return EvidenceItem(
            id=row["id"],
            case_id=row["case_id"],
            source_type=EvidenceSourceType(row["source_type"]),
            semantic_type=EvidenceType(row["semantic_type"]),
            file_path=row["file_path"],
            raw_content=row["raw_content"],
            extracted_facts=facts,
            confidence=row["confidence"],
            created_at=row["created_at"],
        )

    async def get_evidence_by_case(self, case_id: str) -> List[EvidenceItem]:
        async with get_db_connection(self.db_path) as db:
            items: List[EvidenceItem] = []
            async with db.execute(
                "SELECT * FROM evidence_items WHERE case_id = ? ORDER BY created_at", (case_id,)
            ) as cursor:
                rows = await cursor.fetchall()
            for row in rows:
                facts = await self._facts_for(db, row["id"])
                items.append(self._row_to_evidence(row, facts))
            return items

    async def get_evidence_by_id(self, evidence_id: str) -> Optional[EvidenceItem]:
        async with get_db_connection(self.db_path) as db:
            async with db.execute(
                "SELECT * FROM evidence_items WHERE id = ?", (evidence_id,)
            ) as cursor:
                row = await cursor.fetchone()
            if not row:
                return None
            facts = await self._facts_for(db, evidence_id)
            return self._row_to_evidence(row, facts)


class ClaimRepository:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    async def create_claim(self, claim: Claim, case_id: str) -> Claim:
        async with get_db_connection(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO claims (
                    id, case_id, description, status, block_reason, supporting_evidence_ids
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    claim.id, case_id, claim.description, claim.status.value,
                    claim.block_reason, json.dumps(claim.supporting_evidence_ids),
                ),
            )
            await db.commit()
        return claim

    async def get_claims_by_case(self, case_id: str) -> List[Claim]:
        async with get_db_connection(self.db_path) as db:
            claims: List[Claim] = []
            async with db.execute(
                "SELECT * FROM claims WHERE case_id = ?", (case_id,)
            ) as cursor:
                async for row in cursor:
                    claims.append(
                        Claim(
                            id=row["id"],
                            description=row["description"],
                            status=ClaimStatus(row["status"]),
                            block_reason=row["block_reason"],
                            supporting_evidence_ids=json.loads(row["supporting_evidence_ids"] or "[]"),
                        )
                    )
            return claims

    async def delete_claims_by_case(self, case_id: str) -> None:
        async with get_db_connection(self.db_path) as db:
            await db.execute("DELETE FROM claims WHERE case_id = ?", (case_id,))
            await db.commit()

    async def update_claim_status(self, claim_id: str, status: ClaimStatus) -> None:
        async with get_db_connection(self.db_path) as db:
            await db.execute("UPDATE claims SET status = ? WHERE id = ?", (status.value, claim_id))
            await db.commit()


class TimelineRepository:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    async def create_event(self, event: TimelineEvent, case_id: str) -> TimelineEvent:
        anomalies_json = json.dumps([a.model_dump() for a in event.anomalies])
        async with get_db_connection(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO timeline_events (
                    id, case_id, timestamp, description, evidence_id,
                    event_type, actor, ip_address, anomalies
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id, case_id, event.timestamp.isoformat(), event.description,
                    event.evidence_id, event.event_type, event.actor, event.ip_address,
                    anomalies_json,
                ),
            )
            await db.commit()
        return event

    async def get_timeline_by_case(self, case_id: str) -> List[TimelineEvent]:
        async with get_db_connection(self.db_path) as db:
            events: List[TimelineEvent] = []
            async with db.execute(
                "SELECT * FROM timeline_events WHERE case_id = ? ORDER BY timestamp", (case_id,)
            ) as cursor:
                async for row in cursor:
                    raw_anomalies = json.loads(row["anomalies"] or "[]")
                    events.append(
                        TimelineEvent(
                            id=row["id"],
                            timestamp=row["timestamp"],
                            description=row["description"],
                            evidence_id=row["evidence_id"],
                            event_type=row["event_type"],
                            actor=row["actor"],
                            ip_address=row["ip_address"],
                            anomalies=[TimelineAnomaly(**a) for a in raw_anomalies],
                        )
                    )
            return events

    async def delete_timeline_by_case(self, case_id: str) -> None:
        async with get_db_connection(self.db_path) as db:
            await db.execute("DELETE FROM timeline_events WHERE case_id = ?", (case_id,))
            await db.commit()


class AuditRepository:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    async def log_entry(self, entry: AuditLogEntry) -> AuditLogEntry:
        async with get_db_connection(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO audit_log (
                    id, case_id, timestamp, pipeline_stage, model_used,
                    prompt_hash, decision, confidence, latency_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.id, entry.case_id, entry.timestamp.isoformat(), entry.pipeline_stage,
                    entry.model_used, entry.prompt_hash, entry.decision, entry.confidence,
                    entry.latency_ms,
                ),
            )
            await db.commit()
        return entry

    async def get_audit_trail(self, case_id: str) -> List[AuditLogEntry]:
        async with get_db_connection(self.db_path) as db:
            entries: List[AuditLogEntry] = []
            async with db.execute(
                "SELECT * FROM audit_log WHERE case_id = ? ORDER BY timestamp", (case_id,)
            ) as cursor:
                async for row in cursor:
                    entries.append(
                        AuditLogEntry(
                            id=row["id"],
                            case_id=row["case_id"],
                            timestamp=row["timestamp"],
                            pipeline_stage=row["pipeline_stage"],
                            model_used=row["model_used"],
                            prompt_hash=row["prompt_hash"],
                            decision=row["decision"],
                            confidence=row["confidence"],
                            latency_ms=row["latency_ms"],
                        )
                    )
            return entries
