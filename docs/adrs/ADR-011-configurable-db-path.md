# ADR-011: Environment-Configurable Database Path

> **Status:** Accepted 2026-08-26.

## Context

Three workflows share one codebase and must not clobber one another's state: the running demo (persistent cases the operator has loaded), the test suite (a throwaway database created and torn down per run), and the reproducible evaluation (its own isolated store). If all three write the same fixed file, tests corrupt demo data and evaluation runs contaminate each other. We needed database-location isolation without branching code paths per environment.

## Decision

The database path is read from the **`DISPUTESHIELD_DB`** environment variable, with a sensible default when unset (`src/database/db.py:31`).

- The default is a local file for interactive use.
- Tests and the evaluation harness set `DISPUTESHIELD_DB` to their own paths, giving each run an isolated store.
- All `*.db` files are git-ignored (root `.gitignore`), so no database — and nothing derived from evidence — is ever committed.

## Consequences

- **Clean isolation with one lever.** Point the variable at a scratch path for tests, a fixed path for the demo, a dedicated path for evaluation — no code change, no per-environment branch.
- **It is configuration, not a secret.** A filesystem path carries no credential; it is logged and inspectable. This keeps it distinct from `GEMINI_API_KEY`, which is env-only *and* never logged (see [docs/security.md](../security.md) §3.4 and [ADR-004](ADR-004-model-selection.md)).
- **Reproducibility.** The evaluation's ability to run against a fresh, isolated database on any machine (see [ADR-009](ADR-009-evaluation-methodology.md)) depends on this indirection.
- Works with [ADR-010](ADR-010-schema-reconciliation.md): whichever database the variable selects is schema-reconciled on startup, so a brand-new eval database is valid immediately.
