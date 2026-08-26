# ADR-012: In-Process Contract Testing

> **Status:** Accepted 2026-08-26.

## Context

The frontend depends on exact backend response shapes (the API contract documented for the workbench rebuild). We wanted an automated check that the real routes still return what the client expects — the kind of thing a live end-to-end test in a browser would catch. But the build/CI environment is sandboxed and blocks socket binding to `localhost`, so we cannot stand up a dev server and drive it with a browser. The choice was: skip contract verification (and risk silent frontend breakage), or find a way to exercise the real routes without a network listener.

## Decision

We verify the contract **in-process** using FastAPI's `TestClient`, which drives the ASGI app directly without binding a port (`backend/scripts/contract_check.py`).

- The check calls the real route handlers against a real (isolated, per [ADR-011](ADR-011-configurable-db-path.md)) database and asserts the response JSON matches the shapes the frontend consumes.
- It runs anywhere the test suite runs — including the sandbox — with no server process and no open socket.

## Consequences

- **The contract is actually checked**, in an environment where a live server is impossible. Frontend-breaking response changes surface as a failed check, not as a runtime error in the browser.
- **It is not a substitute for true end-to-end testing.** It exercises the server side of the contract only: it does not run the real browser, real CORS preflight, real network timing, or the client's rendering. Those remain manually verified and are called out as a gap in [failure-analysis.md](../failure-analysis.md) §10. We state this plainly rather than implying full E2E coverage.
- **Honest about the constraint.** This ADR exists partly to record *why* there is no live-server smoke test in the harness — a sandbox limitation, not an oversight — so a future reader with an unrestricted environment knows to add one.
- Complements the deterministic evaluation ([ADR-009](ADR-009-evaluation-methodology.md)): evaluation proves the decision core is correct; the contract check proves the API surface around it is stable.
