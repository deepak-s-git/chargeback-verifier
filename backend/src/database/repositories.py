import json
from typing import List, Optional

import aiosqlite

from src.domain.enums import CaseStatus, ClaimStatus
from src.domain.models import AuditLogEntry, Claim, DisputeCase, EvidenceItem, TimelineEvent


class CaseRepository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def create_case(self, case: DisputeCase) -> DisputeCase:
        query = """
            INSERT INTO cases (
                id, merchant_id, transaction_id, amount, currency,
                network, category, reason_code, phase, status,
                created_at, updated_at, package_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        await self.db.execute(
            query,
            (
                case.id, case.merchant_id, case.transaction_id, case.amount, case.currency,
                case.network.value, case.category.value, case.reason_code, case.phase.value,
                case.status.value, case.created_at.isoformat(), case.updated_at.isoformat(),
                case.package.model_dump_json() if case.package else None
            )
        )
        await self.db.commit()
        return case

    async def get_case(self, case_id: str) -> Optional[DisputeCase]:
        # A basic implementation. In reality you'd join with evidence and claims to fully reconstruct.
        query = "SELECT * FROM cases WHERE id = ?"
        async with self.db.execute(query, (case_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            
            # Simplified mock load for now
            return DisputeCase(
                id=row["id"],
                merchant_id=row["merchant_id"],
                transaction_id=row["transaction_id"],
                amount=row["amount"],
                currency=row["currency"],
                network=row["network"],
                category=row["category"],
                reason_code=row["reason_code"],
                phase=row["phase"],
                status=row["status"],
            )
            
    async def update_case(self, case: DisputeCase) -> DisputeCase:
        query = """
            UPDATE cases SET
                phase = ?, status = ?, updated_at = ?, package_data = ?
            WHERE id = ?
        """
        await self.db.execute(
            query,
            (
                case.phase.value, case.status.value, case.updated_at.isoformat(),
                case.package.model_dump_json() if case.package else None, case.id
            )
        )
        await self.db.commit()
        return case
        
    async def list_cases(self) -> List[DisputeCase]:
        query = "SELECT * FROM cases ORDER BY created_at DESC"
        cases = []
        async with self.db.execute(query) as cursor:
            async for row in cursor:
                cases.append(DisputeCase(
                    id=row["id"],
                    merchant_id=row["merchant_id"],
                    transaction_id=row["transaction_id"],
                    amount=row["amount"],
                    currency=row["currency"],
                    network=row["network"],
                    category=row["category"],
                    reason_code=row["reason_code"],
                    phase=row["phase"],
                    status=row["status"],
                ))
        return cases


class EvidenceRepository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db
        
    async def create_evidence(self, evidence: EvidenceItem) -> EvidenceItem:
        query = """
            INSERT INTO evidence_items (
                id, case_id, source_type, semantic_type, file_path,
                raw_content, confidence, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        await self.db.execute(
            query,
            (
                evidence.id, evidence.case_id, evidence.source_type.value,
                evidence.semantic_type.value, evidence.file_path, evidence.raw_content,
                evidence.confidence, evidence.created_at.isoformat()
            )
        )
        
        # Save extracted facts
        for fact in evidence.extracted_facts:
            fact_query = """
                INSERT INTO extracted_facts (
                    evidence_id, type, value, confidence, extraction_method,
                    source_file, source_location, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            await self.db.execute(
                fact_query,
                (
                    evidence.id, fact.type.value, fact.value, fact.confidence,
                    fact.extraction_method.value, fact.provenance.source_file,
                    fact.provenance.source_location, fact.provenance.content_hash
                )
            )
            
        await self.db.commit()
        return evidence

    async def get_evidence_by_case(self, case_id: str) -> List[EvidenceItem]:
        # Stub
        return []

    async def get_evidence_by_id(self, evidence_id: str) -> Optional[EvidenceItem]:
        # Stub
        return None


class ClaimRepository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db
        
    async def create_claim(self, claim: Claim, case_id: str) -> Claim:
        query = """
            INSERT INTO claims (
                id, case_id, description, status, block_reason, supporting_evidence_ids
            ) VALUES (?, ?, ?, ?, ?, ?)
        """
        await self.db.execute(
            query,
            (
                claim.id, case_id, claim.description, claim.status.value,
                claim.block_reason, json.dumps(claim.supporting_evidence_ids)
            )
        )
        await self.db.commit()
        return claim
        
    async def get_claims_by_case(self, case_id: str) -> List[Claim]:
        # Stub
        return []
        
    async def update_claim_status(self, claim_id: str, status: ClaimStatus) -> None:
        query = "UPDATE claims SET status = ? WHERE id = ?"
        await self.db.execute(query, (status.value, claim_id))
        await self.db.commit()


class TimelineRepository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db
        
    async def create_event(self, event: TimelineEvent, case_id: str) -> TimelineEvent:
        query = """
            INSERT INTO timeline_events (
                id, case_id, timestamp, description, evidence_id, anomalies
            ) VALUES (?, ?, ?, ?, ?, ?)
        """
        anomalies_json = json.dumps([a.model_dump() for a in event.anomalies])
        await self.db.execute(
            query,
            (
                event.id, case_id, event.timestamp.isoformat(), event.description,
                event.evidence_id, anomalies_json
            )
        )
        await self.db.commit()
        return event
        
    async def get_timeline_by_case(self, case_id: str) -> List[TimelineEvent]:
        # Stub
        return []


class AuditRepository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db
        
    async def log_entry(self, entry: AuditLogEntry) -> AuditLogEntry:
        query = """
            INSERT INTO audit_log (
                id, case_id, timestamp, pipeline_stage, model_used,
                prompt_hash, decision, confidence, latency_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        await self.db.execute(
            query,
            (
                entry.id, entry.case_id, entry.timestamp.isoformat(), entry.pipeline_stage,
                entry.model_used, entry.prompt_hash, entry.decision, entry.confidence,
                entry.latency_ms
            )
        )
        await self.db.commit()
        return entry
        
    async def get_audit_trail(self, case_id: str) -> List[AuditLogEntry]:
        # Stub
        return []
