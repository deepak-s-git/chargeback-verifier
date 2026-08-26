# ADR-010: Additive Schema Reconciliation for SQLite

> **Status:** Accepted 2026-08-26.

## Context

The schema evolved rapidly during the rebuild, and the datastore is a single-file SQLite database used for the demo, the tests, and local development. A heavyweight migration framework (Alembic-style versioned up/down scripts) is overkill for a buildathon prototype and adds ceremony to every schema tweak. But the naive alternative — dropping and recreating the database — destroys demo cases and audit history, and a hand-edited schema drifts silently between environments. We needed schema evolution that is automatic and safe, without a migration framework and without data loss.

## Decision

We use **additive column reconciliation** at startup.

1. Base tables are created idempotently with `CREATE TABLE IF NOT EXISTS` (`src/database/migrations.py`).
2. `_reconcile_columns(...)` (`src/database/migrations.py:52`) inspects each table's live columns via `PRAGMA table_info` and `ALTER TABLE ... ADD COLUMN` for any column present in the module-level constant `_ADDED_COLUMNS` (`migrations.py:38-49`) but missing from the table.
3. **DDL identifiers come exclusively from that code constant** — never from request input — so the string-built ALTER statements are not injectable (`migrations.py:59,64`; see [docs/security.md](../security.md) §3.3).
4. Connections are per-operation with `foreign_keys=ON`, `journal_mode=WAL`, and `busy_timeout=5000` (`src/database/db.py:34-49`).

## Consequences

- **Forward-compatible, zero-ceremony evolution.** Adding a column is a one-line change to `_ADDED_COLUMNS`; existing databases self-heal on next startup with their data intact.
- **Deliberately not a full migration tool.** It handles additive columns only — no drops, renames, type changes, backfills, or downgrades. For destructive changes the honest path is to delete the local `*.db` (git-ignored) and let the base schema recreate it. This limit is accepted for a prototype and documented rather than hidden.
- **Safe by construction.** Because identifiers are a code constant, the one place we build SQL by string concatenation carries no injection risk — the property that lets [docs/security.md](../security.md) state "SQL-injection risk in the query layer: effectively none."
- Pairs with [ADR-011](ADR-011-configurable-db-path.md): reconciliation runs against whichever database `DISPUTESHIELD_DB` points at, so eval/test/dev schemas each self-heal independently.
