# Design system

**DisputeShield — the token set, five-intent color language, and component primitives the Evidence Workbench is built from.**

*Scope: the rebuilt DisputeShield frontend (`frontend/src`). Every token, class, and version below is verified against the current source with `path:line` citations. Verified 2026-08-26 against `frontend/src`. Companion documents: [UX](ux.md) · [Product](product.md) · [Architecture](architecture.md).*

---

## 1. Philosophy

Three ideas hold the visual layer together:

1. **CSS-first Tailwind v4.** There is **no `tailwind.config.js`** (confirmed absent). Tailwind is pulled in with a single `@import 'tailwindcss';` (`frontend/src/index.css:1`) and wired through the `@tailwindcss/vite` plugin (`frontend/vite.config.ts`), not PostCSS. Layout utilities (flex/grid/spacing) are applied inline in JSX; color, surface, and component semantics live in **one** stylesheet, `frontend/src/index.css`.
2. **Token-driven.** Colors, radii, and shadows are CSS custom properties. Component classes reference them via `var(--token)` and never hard-code a hex, so the palette stays controlled from a single declaration block.
3. **Intent-based, not ad-hoc color.** Every risk-bearing domain enum is reduced to one of **five semantic intents** in `frontend/src/lib/status.ts`, and components pick a class from that intent (`frontend/src/components/ui.tsx`). A color means the same thing in every panel because the meaning is decided once.

> **Where the tokens actually live.** In Tailwind v4 the `@theme` directive is what generates utility classes from tokens. Here `@theme` defines **only the two font families** (`frontend/src/index.css:18-23`); those become the `font-sans` / `font-mono` utilities. The rest of the design tokens — palette, radius, shadow — are declared in a plain `:root` block (`:25-74`) and consumed through `var()`. So the palette is deliberately *not* exposed as Tailwind color utilities; it is reached only through the component classes below.

```css
@theme {
  --font-sans: "Inter", "SF Pro Text", ui-sans-serif, system-ui, -apple-system,
    "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --font-mono: "JetBrains Mono", "SF Mono", ui-monospace, SFMono-Regular, Menlo,
    Consolas, "Liberation Mono", monospace;
}
```

---

## 2. Color tokens

All values below are the literal declarations in the `:root` block of `frontend/src/index.css:25-74`. The design is a fixed dual-tone layout: a light, paper-like analysis **canvas** beside a near-black **command rail**.

### 2.1 Neutrals & surfaces (`:26-38`)

| Token | Value | Role |
|---|---|---|
| `--canvas` | `#f5f5f6` | app background |
| `--surface` | `#ffffff` | card surface |
| `--surface-2` | `#fafafb` | subtle raised surface (table headers, hover) |
| `--surface-inset` | `#f4f4f5` | inset wells, badges, meter track |
| `--ink` | `#17181c` | headings / primary text |
| `--ink-2` | `#3b3d45` | body text |
| `--muted` | `#6b6d78` | secondary text |
| `--faint` | `#9a9ca6` | tertiary / meta text |
| `--hair` | `#e6e6ea` | hairline borders |
| `--hair-strong` | `#d6d7dd` | emphasized borders, inputs |

### 2.2 Brand — indigo (`:40-46`)

| Token | Value | Role |
|---|---|---|
| `--brand` | `#4338ca` | primary action, active states |
| `--brand-hover` | `#3730a3` | primary hover |
| `--brand-ink` | `#ffffff` | text on brand |
| `--brand-050` | `#eef1fe` | brand tint (selected rows, badges) |
| `--brand-100` | `#e0e4fb` | brand tint border |
| `--ring` | `rgba(67, 56, 202, 0.35)` | focus ring |

### 2.3 Command rail — near-black (`:48-55`)

| Token | Value | Role |
|---|---|---|
| `--rail` | `#101116` | rail background (also `.raw` code blocks) |
| `--rail-2` | `#16171d` | rail hover / chips |
| `--rail-hair` | `#26272f` | rail borders |
| `--rail-ink` | `#e8e8ec` | rail primary text |
| `--rail-muted` | `#9698a3` | rail secondary text |
| `--rail-faint` | `#63656f` | rail meta / labels |
| `--rail-active` | `#1e2029` | active nav item |

---

## 3. The five-intent system

Intents are the backbone of the whole UI. The union type is the single source of truth (`frontend/src/lib/status.ts:21`):

```ts
export type Intent = 'pos' | 'warn' | 'neu' | 'crit' | 'info';
```

Each intent is a triple — foreground / background / border — declared together in `:root` (`frontend/src/index.css:57-62`):

```css
--pos: #067a54;   --pos-bg: #ecfdf3;  --pos-bd: #a6e9c8;
--warn: #b45309;  --warn-bg: #fff8ec; --warn-bd: #fbdca0;
--neu: #4a5568;   --neu-bg: #f1f3f6;  --neu-bd: #dde1e8;
--crit: #c02626;  --crit-bg: #fef2f2; --crit-bd: #f6bcbc;
--info: #2563a8;  --info-bg: #eef5fd; --info-bd: #b6d4f0;
```

| Intent | Meaning | fg | bg | border | Where used |
|---|---|---|---|---|---|
| `pos` | positive / good | `#067a54` | `#ecfdf3` | `#a6e9c8` | contest, satisfied, verified, won, score ≥ 75 |
| `warn` | caution | `#b45309` | `#fff8ec` | `#fbdca0` | review, partial, medium severity |
| `neu` | neutral | `#4a5568` | `#f1f3f6` | `#dde1e8` | insufficient/abstain, missing, draft, low |
| `crit` | critical | `#c02626` | `#fef2f2` | `#f6bcbc` | contradicted, blocked, lost, high severity |
| `info` | informational | `#2563a8` | `#eef5fd` | `#b6d4f0` | submitted (informational status) |

The token names are the abbreviated forms (`pos`, `warn`, `neu`, `crit`, `info`), not `positive`/`warning`/etc. — the abbreviations are canonical across the type, the mapping functions, and the CSS class names.

---

## 4. Domain → intent mapping

`frontend/src/lib/status.ts` is the only place a domain status becomes an intent. Feature components call these functions and pass the result to a primitive; they never choose a color themselves.

| Function | Source | Domain value → intent |
|---|---|---|
| `recommendationIntent` | `status.ts:23` | `CONTEST`→`pos`, `REVIEW`→`warn`, `INSUFFICIENT`→`neu`, `ABSTAIN`→`neu` |
| `gateIntent` | `status.ts:36` | `READY`→`pos`, `NEEDS_REVIEW`→`warn`, `MANDATORY_REVIEW`→`crit`, `NOT_RECOMMENDED`→`neu` |
| `requirementIntent` | `status.ts:49` | `SATISFIED`→`pos`, `PARTIALLY_SATISFIED`→`warn`, `CONTRADICTED`→`crit`, `MISSING`→`neu`, `NOT_APPLICABLE`→`neu` |
| `claimIntent` | `status.ts:64` | `VERIFIED`→`pos`, `NEEDS_REVIEW`→`warn`, `BLOCKED`→`crit`, `DRAFT`→`neu` |
| `caseStatusIntent` | `status.ts:77` | `WON`/`PACKAGE_READY`→`pos`, `LOST`→`crit`, `REVIEW_REQUIRED`→`warn`, `SUBMITTED`→`info`, default→`neu` |
| `severityIntent` | `status.ts:93` | `HIGH`→`crit`, `MEDIUM`→`warn`, `LOW`→`neu`, default→`neu` (case-insensitive) |
| `scoringFactorIntent` | `status.ts:106` | `POSITIVE`→`pos`, `NEGATIVE`→`crit`, `MISSING`→`neu` |
| `scoreIntent` | `status.ts:117` | 0–100 gauge: `≥75`→`pos`, `≥50`→`warn`, `≥25`→`neu`, else→`crit` |

---

## 5. Component primitives & the class contract

Presentational primitives live in `frontend/src/components/ui.tsx` — no data fetching, no business logic. They translate an `Intent` into a class via three lookup records and render standard chrome.

| Primitive | Source | Props | Notes |
|---|---|---|---|
| `Pill` | `ui.tsx:37` | `intent`, `children`, `icon?`, `dot?` | status/recommendation chip; `dot` adds a leading dot |
| `Badge` | `ui.tsx:56` | `intent?`, `mono?`, `icon?`, `children`, `title?` | small metadata tag; `mono` uses the mono face |
| `Meter` | `ui.tsx:78` | `value` (0–1), `intent?` | fills a track; value is clamped to `[0,1]` |
| `Loading` | `ui.tsx:87` | `label?` | spinner + `role="status"` |
| `ErrorState` | `ui.tsx:96` | `message`, `onRetry?` | `role="alert"`, optional retry button |
| `EmptyState` | `ui.tsx:116` | `icon?`, `title`, `hint?` | defaults to an `Inbox` icon |
| `Panel` | `ui.tsx:141` | `title?`, `eyebrow?`, `right?`, `children`, `bodyStyle?` | titled card with standard header chrome |

### The `.pill` / `.badge` / `.meter` contract

Each primitive maps `Intent` → class name (`ui.tsx:13-35`). The CSS classes are defined in `frontend/src/index.css` (pills `:166-170`, badges `:199-202`, meter fills `:341-344`). The mapping is **not** uniform across the three — some intents deliberately fall back to the base class:

| Intent | `.pill--` (`:166`) | `.badge--` (`:199`) | `.meter__fill--` (`:341`) |
|---|---|---|---|
| `pos` | `pill--pos` | `badge--pos` | `meter__fill--pos` |
| `warn` | `pill--warn` | `badge--warn` | `meter__fill--warn` |
| `neu` | `pill--neu` | *(none → base `.badge`)* | `meter__fill--neu` |
| `crit` | `pill--crit` | `badge--crit` | `meter__fill--crit` |
| `info` | `pill--info` | `badge--brand` | *(none → base fill = `--brand`)* |

Two intentional gaps: a `neu` **badge** carries no modifier (it uses the default inset styling, `:182-193`), an `info` **badge** reuses `badge--brand` (`:199`), and an `info` **meter** falls through to the default fill, which is `--brand` (`:335-340`). There is no `.badge--neu`, `.badge--info`, or `.meter__fill--info` in the stylesheet (grep-confirmed). Pills are the only family with all five modifiers.

```tsx
// ui.tsx:21 — empty string = "use the base class"
const BADGE_CLASS: Record<Intent, string> = {
  pos: 'badge--pos', warn: 'badge--warn', neu: '', crit: 'badge--crit', info: 'badge--brand',
};
```

Beyond the intent trio, `index.css` also defines the rest of the workbench vocabulary — `.card`/`.card__header`/`.card__body`, `.btn` (+ `--primary`/`--ghost`/`--sm`), the command-rail set (`.rail`, `.nav-item`, `.btn-rail`, `.rail-badge`), `.dtable`, `.banner` (`--pos`/`--warn`/`--crit`/`--neu`), `.kv`, `.prov`, `.tab`, `.input`/`.select`, `.modal`, and `.raw`.

---

## 6. Typography, spacing & radius

### Type

- **Families** are the only `@theme` tokens: `--font-sans` (Inter-led) and `--font-mono` (JetBrains Mono-led) (`index.css:18-23`).
- **Base** is `14px` / `line-height 1.5` on `body`, with stylistic sets `"cv02" "cv03" "cv04" "cv11"` enabled (`:86-97`).
- **Numeric/technical values** use `.mono` — tabular figures + slashed zero (`font-variant-numeric: tabular-nums slashed-zero`, `:100-104`); `.tnum` gives tabular figures alone.
- **Named type roles:** `.eyebrow` (10.5px, 600, uppercase, 0.09em tracking, `--faint`, `:112-118`) and `.section-title` (12.5px, 650, `--ink`, `:120-125`).

There is **no font-size scale token** — every other size is set per component class (e.g. `.pill` 11.5px, `.badge` 11px, `.btn` 13px). Weights lean on the 550–650 range for a dense, technical feel.

### Radius (`:64-68`)

| Token | Value | Typical use |
|---|---|---|
| `--r-xs` | `4px` | badges, small buttons, chips |
| `--r-sm` | `6px` | buttons, inputs, nav items |
| `--r-md` | `8px` | insets, banners, rail mark |
| `--r-lg` | `12px` | cards |
| `--r-xl` | `16px` | modal |

### Shadow (`:70-73`)

`--shadow-xs` / `--shadow-sm` / `--shadow-md` / `--shadow-lg`, all tinted with `rgba(19,20,25, …)`. Cards use `xs`; the modal uses `lg`.

### Spacing

There are **no custom spacing tokens**. Per the file's own header comment, "layout utilities (flex/grid/spacing) are applied inline via Tailwind" — spacing uses Tailwind's default scale in JSX, and component-internal padding is hard-coded in `index.css`.

---

## 7. Tooling & dependency versions

From `frontend/package.json` (ranges as declared). Scripts: `dev` → `vite`, `build` → `tsc -b && vite build`, `lint` → `oxlint`, `preview` → `vite preview`.

| Package | Version | Role |
|---|---|---|
| `react` / `react-dom` | `^19.2.8` | UI runtime (React 19) |
| `axios` | `^1.19.0` | HTTP client to the backend API |
| `lucide-react` | `^1.34.0` | icon set |
| `vite` | `^8.2.2` | dev server / bundler |
| `@vitejs/plugin-react` | `^6.1.0` | React plugin for Vite |
| `tailwindcss` | `^4.3.3` | Tailwind v4 |
| `@tailwindcss/vite` | `^4.3.3` | Tailwind's Vite plugin (no PostCSS, no config file) |
| `typescript` | `~6.0.2` | type system |
| `oxlint` | `^1.79.0` | linter |
| `@types/node` | `^24.13.3` | Node types |
| `@types/react` | `^19.2.18` | React types |
| `@types/react-dom` | `^19.2.4` | React DOM types |

Vite registers `react()` and `tailwindcss()` and proxies `/api` → `http://localhost:8000` (`frontend/vite.config.ts`).

---

## 8. Honestly absent

Things a reader might expect that this system deliberately does **not** have:

- **No dark-mode theming for the canvas.** There is no `prefers-color-scheme` query, `.dark` class, or `data-theme` switch (grep-confirmed). The dark command rail is a *fixed* region of a dual-tone layout, not a toggleable theme; the analysis canvas is always light.
- **No responsive tokens or breakpoints.** `index.css` contains **zero** `@media` queries. The shell is a fixed desktop layout — a 300px rail (`.rail`, `:564-572`) beside a fluid `.main`, inside a `height: 100vh` `.app-shell` (`:562`). There is no mobile/tablet adaptation.
- **No palette exposed as Tailwind utilities.** Because the color tokens live in `:root` rather than `@theme`, there are no `bg-brand` / `text-crit`-style utilities; color is reached only through the component classes in §5.
- **No spacing or font-size scale tokens** (see §6).

---

*Consistency note: this doc is descriptive, not aspirational — it records the tokens and classes that exist today. If a value here disagrees with `frontend/src`, the source wins; re-verify and update this file.*
