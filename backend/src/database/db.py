import contextlib
from typing import AsyncGenerator

import aiosqlite


DB_PATH = "disputeshield.db"


@contextlib.asynccontextmanager
async def get_db_connection(db_path: str = DB_PATH) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Async context manager for aiosqlite database connection."""
    conn = await aiosqlite.connect(db_path)
    # Enable foreign keys and row factory
    await conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = aiosqlite.Row
    try:
        yield conn
    finally:
        await conn.close()


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Dependency injection function for FastAPI."""
    async with get_db_connection() as conn:
        yield conn
