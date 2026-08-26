"""SQLite connection management.

The application uses a *connection-per-operation* model rather than one
long-lived shared connection. A single ``aiosqlite`` connection serialises every
statement through one background thread and, if any operation leaves it in a bad
state, poisons the whole process; sharing it across concurrent requests is a
well-known source of subtle stalls. Opening a short-lived connection per
repository call is simple, correct under concurrency, and — with WAL journaling
and a busy timeout enabled below — perfectly adequate for this workload.

Every connection is configured identically:

* ``foreign_keys = ON`` so ``ON DELETE CASCADE`` is actually enforced;
* ``journal_mode = WAL`` so readers never block the writer and cross-connection
  reads observe the last committed state;
* ``busy_timeout = 5000`` so a briefly-locked database retries rather than
  raising immediately;
* a ``Row`` factory so rows are addressable by column name.
"""

import contextlib
from typing import AsyncGenerator

import aiosqlite

import os

# Database file path. Overridable via ``DISPUTESHIELD_DB`` so tests and alternate
# deployments can point at a throwaway or relocated database without touching the
# default development file.
DB_PATH = os.environ.get("DISPUTESHIELD_DB", "disputeshield.db")


async def _configure(conn: aiosqlite.Connection) -> None:
    await conn.execute("PRAGMA foreign_keys = ON")
    await conn.execute("PRAGMA journal_mode = WAL")
    await conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = aiosqlite.Row


@contextlib.asynccontextmanager
async def get_db_connection(db_path: str = DB_PATH) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Yield a fully-configured, short-lived aiosqlite connection."""
    conn = await aiosqlite.connect(db_path)
    try:
        await _configure(conn)
        yield conn
    finally:
        await conn.close()


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """FastAPI dependency yielding a per-request connection."""
    async with get_db_connection() as conn:
        yield conn
