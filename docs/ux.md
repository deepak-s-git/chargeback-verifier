# Frontend UX & Information Architecture

**How the DisputeShield workbench is laid out, how it loads data, and what it deliberately does — and does not — do.**

*Scope: the rebuilt DisputeShield frontend — its shell, the case workspace, and the client that feeds them. Every claim below is verified against the current source with `path:line` citations (paths relative to `frontend/src`). Verified 2026-08-26 against `frontend/src`. Companion documents: [Design system](design-system.md) · [Product](product.md) · [Architecture](architecture.md) · [Failure analysis](failure-analysis.md).*

---

## 1. Orientation — the two-pane shell

The whole application is one screen: a **two-pane shell** that fills the viewport and never scrolls as a unit (`.app-shell { display: flex; height: 100vh; overflow: hidden; }`, `index.css:562`; rendered at `App.tsx:81`).

| Pane | Element | Styling | Role |
|---|---|---|---|
| **Command rail** (left) | `<aside className="rail">` (`App.tsx:83`) | `width: 300px; flex: none; background: var(--rail)` (`index.css:564-567`), where `--rail: #101116` (`index.css:49`) | A fixed ~300px dark rail — never grows or shrinks — holding all global actions and the case list |
| **Main canvas** (right) | `<main className="main">` (`App.tsx:127`) | `flex: 1; min-width: 0; background: var(--canvas)` (`index.css:616`), where `--canvas: #f5f5f6` (`index.css:27`) | A light working surface that shows exactly one thing at a time |

The canvas is a strict single-slot: it renders the selected case's workspace, or — when nothing is selected — a loading spinner, an error, or an empty "No case selected" prompt with a *Load demo set* shortcut (`App.tsx:128-153`). There is no dashboard, no multi-case view; the mental model is "pick one case on the left, work it on the right."

---

## 2. Navigation & the command rail

Top to bottom the rail is: **brand** (`App.tsx:84-92`) → **actions** (`App.tsx:94-102`) → **case list** (`App.tsx:104-117`) → **footer tagline** "Defense-only · never auto-submits · every claim traced to evidence" (`App.tsx:119-123`).

The two global actions live here and nowhere else:

- **New case** opens the modal (`App.tsx:95-97`).
- **Load demo set** calls `loadDemo()`, refreshes the list, and selects the first created case (`App.tsx:65-78, 98-101`).

The list region resolves its own async states inline rather than through the shared primitives: a spinner while loading (`App.tsx:106-109`), red text on error (`App.tsx:110-113`), otherwise `<CaseList>` (`App.tsx:115`).

`CaseList` (`components/CaseList.tsx`) is purely prop-driven — no fetching (docstring `1-6`). Each case is a `<button className="nav-item">` with `aria-current={active}` (`CaseList.tsx:54-60`) showing id, transaction/dispute reference, network, a status dot, and amount. With no cases it renders an `EmptyState` "No cases yet" (`CaseList.tsx:36-45`).

Selection is a single piece of shell state (`selectedId`, `App.tsx:24`): the first case is auto-selected on initial load (`App.tsx:44`), a freshly created case is selected on success (`App.tsx:61`), and the demo loader selects the first seeded case (`App.tsx:71-72`).

---

## 3. The case workspace and its seven tabs

The workspace is `components/CaseWorkspace.tsx`, mounted by the shell as `<CaseWorkspace key={selectedId} caseId={selectedId} />` (`App.tsx:129`). The **`key` is load-bearing**: keying on the case id forces a full remount whenever the selection changes, so the active tab, every lazy-fetch, and all child state reset — no state leaks between cases (docstring `9-11`).

On mount it issues **two fetches, once**: `useApi(() => getCase(caseId), caseId)` (`CaseWorkspace.tsx:39`) and `useApi(() => getAnalysis(caseId), caseId)` (`CaseWorkspace.tsx:40`). Rendering is gated on both: a `Loading` state ("Analysing case…") while either is in flight (`CaseWorkspace.tsx:50-56`), an `ErrorState` with retry if either fails (`CaseWorkspace.tsx:57-63`), and `null` until both resolve (`CaseWorkspace.tsx:64`) — so no tab ever paints partial data.

There are **seven tabs**, declared in this order at `CaseWorkspace.tsx:70-78` and typed by the `TabKey` union at line `29`. The active tab is local state (`tab`, default `overview`, `CaseWorkspace.tsx:41`); the body is a conditional switch (`CaseWorkspace.tsx:133-148`).

The important architectural split is **how each tab gets its data**:

| # | Tab | Renders | Data | Fetched |
|---|---|---|---|---|
| 1 | Overview | `CaseDashboard` | `case` + `analysis` props | once, on workspace mount |
| 2 | Requirements | `RequirementMatrix` | `analysis.requirements`, `analysis.ce30` | once |
| 3 | Score | `ScoreBreakdown` | `analysis.score` / `recommendation` / `gate_*` | once |
| 4 | Timeline | `Timeline` | `analysis.timeline` | once |
| 5 | Evidence | `EvidenceExplorer` | `case.evidence_items` | once |
| 6 | Package | `PackageViewer` | `getPackage(caseId)` | **lazily, on first tab open** |
| 7 | Audit | `AuditTrail` | `getAuditTrail(caseId)` | **lazily, on first tab open** |

- **Tabs 1–5 are prop-driven.** They read from the two payloads already in memory — the whole of Overview, Requirements, Score, Timeline, and Evidence is served from the single `getCase` + `getAnalysis` fetch pair (`CaseWorkspace.tsx:39-40, 133-146`). Switching among these tabs triggers no network activity.
- **Tabs 6–7 lazy-fetch.** `PackageViewer` and `AuditTrail` receive only `caseId` (`CaseWorkspace.tsx:147-148`) and each owns its own `useApi` call — `getPackage` (`PackageViewer.tsx:52`) and `getAuditTrail` (`AuditTrail.tsx:24`). Because they are conditionally mounted only while their tab is active, the request fires on first open (and re-fires on return, since leaving the tab unmounts them).

The header above the tabs shows case identity, network/reason-code badges, status pill, amount, and a response-deadline pill that turns critical when overdue (`CaseWorkspace.tsx:82-111`).

---

## 4. Async state handling (`useApi`)

Every real fetch flows through one small generic hook, `useApi<T>(fetcher, depKey, enabled = true)` (`lib/useApi.ts:27`), which returns an `AsyncState<T>` of `{ data, loading, error, reload }` (`lib/useApi.ts:12-18`). It exists to give the UI the states the pre-rebuild mock never had (docstring `1-7`). It backs `CaseWorkspace`, `PackageViewer`, and `AuditTrail`; the shell's list fetch is the one hand-rolled exception (`App.tsx:40-55`).

- **Loading** is initialised to `enabled` and set true around each run (`lib/useApi.ts:33, 46`).
- **Error** is already reduced to a human-readable string by the API layer — an `ApiError.message`, else a generic fallback (`lib/useApi.ts:53-54`).
- **Stale-result cancellation:** changing `depKey` (the case id) cancels the in-flight promise, so a fast case switch never paints the previous case's data (`lib/useApi.ts:45, 59-62`).
- **`reload()`** bumps a nonce to re-run the fetcher (`lib/useApi.ts:64`); it is what every `ErrorState` retry button calls.
- **`enabled = false`** short-circuits with no request (`lib/useApi.ts:41-44`) — the hook's built-in lazy path, though the workspace currently achieves laziness by conditional mounting instead.

These states are surfaced by the shared primitives in `components/ui.tsx`:

| State | Primitive | Accessibility hook |
|---|---|---|
| Loading | `Loading` (spinner + label) | `role="status" aria-live="polite"` (`ui.tsx:89`) |
| Error | `ErrorState` (message + optional Retry) | `role="alert"` (`ui.tsx:98`) |
| Empty | `EmptyState` (icon + title + hint) | none — plain block (`ui.tsx:116-138`) |

`CaseWorkspace` wires `Loading`/`ErrorState` (`CaseWorkspace.tsx:53, 60`); `PackageViewer` (`54-55`) and `AuditTrail` (`26-27`) do the same and additionally render an `EmptyState` when the fetch returns an empty list (`AuditTrail.tsx:30-41`). `EvidenceExplorer` shows an `EmptyState` "No evidence ingested" when a case has none (`EvidenceExplorer.tsx:121-133`).

---

## 5. Real-data-only principle

**Everything on screen is fetched from the backend or derived from it; the frontend invents no numbers.** The shell docstring states it plainly — "All data is real" (`App.tsx:7-9`) — and the audit view renders "the backend's real fields … with nothing invented" (`AuditTrail.tsx:1-8`).

The pre-rebuild UI displayed fabricated **win-probability and fee** figures; those were removed in the rewrite. `useApi`'s own docstring frames the rebuild as adding "the three states every real fetch has and the mock UI never had" (`lib/useApi.ts:1-7`).

This is the frontend expression of the backend's never-invent-evidence stance (see [Security](security.md) §2): the UI prefers an empty state or a `BLOCKED` claim over a comforting invented metric. `PackageViewer` surfaces block reasons verbatim (`PackageViewer.tsx:32-37`) rather than papering over unsupported claims, and states plainly that the network submission is a **draft**, never transmitted (docstring `6-10`).

---

## 6. Semantic status encoding

All colour *meaning* is centralised in `lib/status.ts`. Every risk-bearing enum in the domain is reduced to one of five **intents** — `pos | warn | neu | crit | info` (`lib/status.ts:21`) — and components select a `.pill--{intent}` / `.badge--{intent}` / `.meter__fill--{intent}` class rather than hard-coding a colour (`ui.tsx:13-35`). [Design system](design-system.md) owns the token values; this section covers only the mapping and where it is applied.

The recommendation mapping (`recommendationIntent`, `lib/status.ts:23-34`):

| Recommendation | Intent | Reads as |
|---|---|---|
| `CONTEST` | `pos` | positive — evidence supports contesting |
| `REVIEW` | `warn` | caution — route to a human |
| `INSUFFICIENT` | `neu` | neutral — not enough to act on |
| `ABSTAIN` | `neu` | neutral — the engine declines to recommend |

The same recommendation renders identically in the three places it appears: the Overview header (`CaseDashboard.tsx:120`), the Score panel (`ScoreBreakdown.tsx:107`), and the Package disposition (`PackageViewer.tsx:92`). `lib/status.ts` maps the other enums the same way — gate status, requirement/claim status, severity, scoring-factor sign, case status, and a 0–100 score band (`lib/status.ts:36-123`) — so a colour carries one meaning across every panel.

---

## 7. Accessibility — present vs. missing

Accessibility is **partial**, and this section is honest about which half is which.

**Present:**

- Async states are announced: `role="status" aria-live="polite"` on `Loading` (`ui.tsx:89`) and `role="alert"` on `ErrorState` (`ui.tsx:98`).
- The active case in the command rail carries `aria-current` (`CaseList.tsx:59`).
- The modal's close control is labelled `aria-label="Close"` (`NewCaseModal.tsx:119`); its first field is `autoFocus`ed (`NewCaseModal.tsx:165`); decorative status dots are `aria-hidden` (`CaseList.tsx:72`).

**Missing:**

- **The workspace tab bar has no tab semantics.** The seven tabs are plain `<button>`s carrying only a visual `tab--active` class (`CaseWorkspace.tsx:116-126`): no `role="tab"`/`role="tablist"`, no `aria-selected`, and — unlike the rail's case list — no `aria-current`. A screen reader hears seven unlabelled buttons, not a selectable tab set. (So `aria-current` marks the active *case*, but not the active *tab*.)
- **The new-case modal has no dialog semantics.** No `role="dialog"`/`aria-modal`, no focus trap, and no Escape-to-close — there is no keydown handler anywhere in the app. It closes only by backdrop mousedown (`NewCaseModal.tsx:112`), the Cancel button (`:258`), or the X (`:119`).

See [Failure analysis](failure-analysis.md) §10 for the consolidated gap register.

---

## 8. Responsive & known UX gaps

Three gaps are real, load-bearing, and documented rather than hidden.

**1. There is no upload UI.** `uploadEvidence` is fully implemented in the client (`lib/api.ts:100-112`) but **no component imports it**; likewise `analyzeCase` (`lib/api.ts:80`) and `getTimeline` (`lib/api.ts:88`) are exported and unused — three of the client's ~ten functions are dead ends. The one that matters for UX: nothing in the interface can attach a file to a case. Yet the copy implies otherwise — the Evidence tab's empty state says "Add evidence from the case's intake, or load the demo set…" (`EvidenceExplorer.tsx:125-129`) and the new-case modal says "Add evidence from the Evidence tab after the case is created" (`NewCaseModal.tsx:245-248`), while neither surface has an upload control. **Evidence currently enters only via the demo loader** (`loadDemo`, `App.tsx:65-78`) **or a direct API call.** (`analyzeCase`/`getTimeline` are unused for benign reasons: the GET `getAnalysis` re-runs analysis idempotently, `lib/api.ts:83-85`, and the Timeline tab reads `analysis.timeline` from that same payload rather than the standalone endpoint.)

**2. Desktop-only.** There are **zero `@media` queries** in `index.css`. The shell is a fixed flex row with a hard 300px rail and `height: 100vh; overflow: hidden` (`index.css:562, 564-566`); nothing reflows. Below roughly a tablet width the rail consumes the canvas and the workbench becomes unusable on small viewports.

**3. Modal accessibility** (as §7): no focus trap, no dialog role, no Escape-to-close.

For the full UX gap register and its remediation notes, see [Failure analysis](failure-analysis.md) §10.

---

*Honesty note: this reference documents the frontend as built, not as aspired to. Where copy promises an affordance the code does not implement (evidence upload), or where accessibility stops short (tab semantics, modal focus management), it is called out rather than smoothed over — the same bar the rest of DisputeShield holds itself to.*
