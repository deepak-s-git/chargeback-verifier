"""Regression tests for the schema self-healing reconciler.

Background: ``CREATE TABLE IF NOT EXISTS`` creates a *missing* table but never
alters an existing one. A database created under an older schema therefore kept
its old columns forever, and the app later crashed with
``table cases has no column named dispute_id`` the moment it tried to persist a
case — which is exactly the path ``POST /api/demo/load`` takes. The fix is
:func:`_reconcile_columns`, called from :func:`init_db`, which adds any post-v1
nullable columns an older on-disk schema is missing.

These tests reproduce that failure mode directly: build an *old-shape, populated*
table, run ``init_db`` against it, and assert the missing columns appear without
destroying the pre-existing row. Expectations are derived from ``_ADDED_COLUMNS``
so the tests automatically cover any column added to that ledger in the future.
"""

import aiosqlite
import pytest

from src.database.migrations import _ADDED_COLUMNS, _reconcile_columns, init_db

# --- Old-shape DDL -----------------------------------------------------------
# These are deliberately the *pre-addition* shapes: every column that appears in
# ``_ADDED_COLUMNS`` is intentionally absent, mirroring a real database file
# created before those columns existed.
_OLD_CASES_DDL = """
    CREATE TABLE cases (
        id TEXT PRIMARY KEY,
        merchant_id TEXT NOT NULL,
        transaction_id TEXT NOT NULL,
        amount REAL NOT NULL,
        currency TEXT NOT NULL,
        network TEXT NOT NULL,
        category TEXT NOT NULL,
        reason_code TEXT NOT NULL,
        phase TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL,
        package_data TEXT
    )
"""

_OLD_TIMELINE_DDL = """
    CREATE TABLE timeline_events (
        id TEXT PRIMARY KEY,
        case_id TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL,
        description TEXT NOT NULL,
        evidence_id TEXT NOT NULL,
        anomalies TEXT
    )
"""


async def _columns(db_path: str, table: str) -> set[str]:
    """Return the set of column names currently defined on ``table``."""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(f"PRAGMA table_info({table})")
        rows = await cursor.fetchall()
    return {row[1] for row in rows}


async def _nullable(db_path: str, table: str) -> set[str]:
    """Return the column names on ``table`` that permit NULL (notnull flag == 0)."""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(f"PRAGMA table_info({table})")
        rows = await cursor.fetchall()
    # PRAGMA table_info columns: (cid, name, type, notnull, dflt_value, pk)
    return {row[1] for row in rows if row[3] == 0}


@pytest.mark.asyncio
async def test_fresh_db_has_all_reconciled_columns(tmp_path):
    """A freshly created database already contains every ledgered column."""
    db_path = str(tmp_path / "fresh.db")
    await init_db(db_path)

    for table, columns in _ADDED_COLUMNS.items():
        present = await _columns(db_path, table)
        for name, _type in columns:
            assert name in present, f"fresh DB missing {table}.{name}"


@pytest.mark.asyncio
async def test_init_db_heals_old_cases_table_without_data_loss(tmp_path):
    """An old, *populated* cases table gains the missing columns; its row survives.

    This is the exact scenario that produced the 500 on ``POST /api/demo/load``:
    a database whose ``cases`` table predates ``dispute_id`` /
    ``transaction_date`` / ``respond_by``.
    """
    db_path = str(tmp_path / "old_cases.db")

    # Build the old shape and populate it, so we also prove ALTER works on a
    # non-empty table (SQLite refuses a NOT NULL add there — hence nullable-only).
    async with aiosqlite.connect(db_path) as db:
        await db.execute(_OLD_CASES_DDL)
        await db.execute(
            """
            INSERT INTO cases (id, merchant_id, transaction_id, amount, currency,
                               network, category, reason_code, phase, status,
                               created_at, updated_at, package_data)
            VALUES ('CASE-legacy', 'MERCH-1', 'TXN-1', 100.0, 'INR', 'VISA',
                    'FRAUD', '10.4', 'FIRST_CHARGEBACK', 'INTAKE',
                    '2026-01-01T00:00:00', '2026-01-01T00:00:00', NULL)
            """
        )
        await db.commit()

    missing = {name for name, _ in _ADDED_COLUMNS["cases"]}
    before = await _columns(db_path, "cases")
    assert not (missing & before), "precondition: old table should lack the new columns"

    await init_db(db_path)

    after = await _columns(db_path, "cases")
    assert missing <= after, f"reconcile did not add {missing - after}"

    # The pre-existing row must be intact, with the new columns defaulting to NULL.
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT merchant_id, dispute_id, transaction_date, respond_by "
            "FROM cases WHERE id = 'CASE-legacy'"
        )
        row = await cursor.fetchone()
    assert row is not None, "legacy row was lost during reconciliation"
    assert row["merchant_id"] == "MERCH-1"
    assert row["dispute_id"] is None
    assert row["transaction_date"] is None
    assert row["respond_by"] is None


@pytest.mark.asyncio
async def test_init_db_heals_old_timeline_table(tmp_path):
    """An old timeline_events table gains event_type / actor / ip_address."""
    db_path = str(tmp_path / "old_timeline.db")
    async with aiosqlite.connect(db_path) as db:
        await db.execute(_OLD_TIMELINE_DDL)
        await db.commit()

    await init_db(db_path)

    after = await _columns(db_path, "timeline_events")
    for name, _type in _ADDED_COLUMNS["timeline_events"]:
        assert name in after, f"reconcile did not add timeline_events.{name}"


@pytest.mark.asyncio
async def test_reconciled_columns_are_nullable(tmp_path):
    """Every reconciled column is added as NULLable (the only safe ALTER here)."""
    db_path = str(tmp_path / "nullable.db")
    async with aiosqlite.connect(db_path) as db:
        await db.execute(_OLD_CASES_DDL)
        await db.execute(_OLD_TIMELINE_DDL)
        await db.commit()

    await init_db(db_path)

    for table, columns in _ADDED_COLUMNS.items():
        nullable = await _nullable(db_path, table)
        for name, _type in columns:
            assert name in nullable, f"{table}.{name} was not added as nullable"


@pytest.mark.asyncio
async def test_reconcile_is_idempotent(tmp_path):
    """Running init_db repeatedly neither errors nor duplicates columns."""
    db_path = str(tmp_path / "idempotent.db")
    async with aiosqlite.connect(db_path) as db:
        await db.execute(_OLD_CASES_DDL)
        await db.commit()

    await init_db(db_path)
    first = await _columns(db_path, "cases")

    # Second and third runs must be no-ops (a duplicate ALTER would raise).
    await init_db(db_path)
    await init_db(db_path)
    third = await _columns(db_path, "cases")

    assert first == third, "column set changed across idempotent re-runs"

    # And a direct double-call of the reconciler on one connection is safe too.
    async with aiosqlite.connect(db_path) as db:
        await _reconcile_columns(db)
        await _reconcile_columns(db)
        await db.commit()
