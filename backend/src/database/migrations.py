"""Database schema initialization.

Idempotent ``CREATE TABLE IF NOT EXISTS`` statements. WAL is enabled here as
well as per-connection so the very first process to touch the file sets the
journal mode durably.

``CREATE TABLE IF NOT EXISTS`` creates a *missing* table but never alters an
existing one, so a database file created under an older schema keeps its old
columns forever. :func:`_reconcile_columns` closes that gap: after the create
statements it adds any post-v1 nullable columns that an older on-disk schema is
missing (via ``ALTER TABLE ... ADD COLUMN``), so existing databases self-heal
instead of failing later with "table X has no column named Y".

Schema notes:
* ``cases`` persists the full dispute context, including ``transaction_date``
  (needed for CE 3.0 windows), ``dispute_id`` and ``respond_by``.
* ``timeline_events`` persists the enriched fields (``event_type``, ``actor``,
  ``ip_address``) the timeline builder derives, so the ``/timeline`` endpoint
  returns the same enriched events the analysis produced.
* ``extracted_facts`` carries the full provenance triple so claim grounding can
  be re-verified after a reload.
"""

import aiosqlite

from src.database.db import DB_PATH
from src.observability.logger import get_logger

logger = get_logger(__name__)

# Columns introduced after the initial schema, per table. SQLite's
# ``CREATE TABLE IF NOT EXISTS`` does not touch an existing table, so a database
# created under an older schema is missing these. Every entry is nullable, which
# is what makes ``ALTER TABLE ... ADD COLUMN`` safe on a populated table (SQLite
# refuses to add a NOT NULL column without a constant default). When a new
# nullable column is added to a CREATE TABLE above, add it here too so old
# databases keep self-healing.
_ADDED_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "cases": [
        ("dispute_id", "TEXT"),
        ("transaction_date", "TIMESTAMP"),
        ("respond_by", "TIMESTAMP"),
    ],
    "timeline_events": [
        ("event_type", "TEXT"),
        ("actor", "TEXT"),
        ("ip_address", "TEXT"),
    ],
}


async def _reconcile_columns(db: aiosqlite.Connection) -> None:
    """Add any post-v1 nullable columns missing from an older on-disk schema.

    Idempotent: a column already present is left untouched, so this is a no-op on
    a freshly created database and a one-time repair on an older one.
    """
    for table, columns in _ADDED_COLUMNS.items():
        cursor = await db.execute(f"PRAGMA table_info({table})")
        rows = await cursor.fetchall()
        existing = {row[1] for row in rows}
        for name, coltype in columns:
            if name not in existing:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {coltype}")
                logger.info("schema_column_added", table=table, column=name, type=coltype)


async def init_db(db_path: str = DB_PATH) -> None:
    """Initialize the database schema (idempotent)."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute("PRAGMA journal_mode = WAL")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                merchant_id TEXT NOT NULL,
                transaction_id TEXT NOT NULL,
                dispute_id TEXT,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                network TEXT NOT NULL,
                category TEXT NOT NULL,
                reason_code TEXT NOT NULL,
                phase TEXT NOT NULL,
                status TEXT NOT NULL,
                transaction_date TIMESTAMP,
                respond_by TIMESTAMP,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                package_data TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS evidence_items (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                source_type TEXT NOT NULL,
                semantic_type TEXT NOT NULL,
                file_path TEXT,
                raw_content TEXT,
                confidence REAL NOT NULL,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS extracted_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evidence_id TEXT NOT NULL,
                type TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence REAL NOT NULL,
                extraction_method TEXT NOT NULL,
                source_file TEXT NOT NULL,
                source_location TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                FOREIGN KEY (evidence_id) REFERENCES evidence_items (id) ON DELETE CASCADE
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS claims (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                block_reason TEXT,
                supporting_evidence_ids TEXT,
                FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS timeline_events (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                description TEXT NOT NULL,
                evidence_id TEXT NOT NULL,
                event_type TEXT,
                actor TEXT,
                ip_address TEXT,
                anomalies TEXT,
                FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS contradictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                claim_a_id TEXT,
                claim_b_id TEXT,
                evidence_a_id TEXT,
                evidence_b_id TEXT,
                description TEXT NOT NULL,
                severity TEXT NOT NULL,
                type TEXT NOT NULL,
                FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                pipeline_stage TEXT NOT NULL,
                model_used TEXT NOT NULL,
                prompt_hash TEXT,
                decision TEXT NOT NULL,
                confidence REAL NOT NULL,
                latency_ms INTEGER NOT NULL,
                FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
            )
        """)

        # Repair older databases whose tables predate columns added above.
        await _reconcile_columns(db)

        await db.commit()


if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
