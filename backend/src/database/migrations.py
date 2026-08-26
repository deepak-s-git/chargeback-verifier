import aiosqlite

from src.database.db import DB_PATH


async def init_db(db_path: str = DB_PATH) -> None:
    """Initialize the database schema."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        
        # Create cases table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cases (
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
        """)
        
        # Create evidence_items table
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
        
        # Create extracted_facts table
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
        
        # Create claims table
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
        
        # Create requirements table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS requirements (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                requirement_def_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                evidence_candidates TEXT,
                source_reference TEXT NOT NULL,
                FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
            )
        """)
        
        # Create timeline_events table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS timeline_events (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                description TEXT NOT NULL,
                evidence_id TEXT NOT NULL,
                anomalies TEXT,
                FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
            )
        """)
        
        # Create contradictions table
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
        
        # Create audit_log table
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
        
        await db.commit()


if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
