/**
 * Presentation helpers. Pure, side-effect-free formatters shared across the
 * workbench so amounts, dates, hashes and enum labels render identically
 * everywhere. Anything that turns backend data into display text lives here.
 */

/** Format a monetary amount using the ISO currency code (falls back gracefully). */
export function formatAmount(amount: number, currency: string): string {
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency,
      maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    // Unknown/invalid currency code — show the code + grouped number.
    return `${currency} ${new Intl.NumberFormat().format(amount)}`;
  }
}

function parse(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** e.g. "15 Jul 2026". */
export function formatDate(iso: string | null | undefined): string {
  const d = parse(iso);
  return d
    ? d.toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' })
    : '—';
}

/** e.g. "15 Jul 2026, 14:22". */
export function formatDateTime(iso: string | null | undefined): string {
  const d = parse(iso);
  return d
    ? d.toLocaleString(undefined, {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '—';
}

/** e.g. "14:22:10". */
export function formatTime(iso: string | null | undefined): string {
  const d = parse(iso);
  return d
    ? d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : '—';
}

/** A compact deadline descriptor: "in 5 days", "today", "3 days ago". */
export function formatDeadline(iso: string | null | undefined): { text: string; overdue: boolean } {
  const d = parse(iso);
  if (!d) return { text: 'No deadline', overdue: false };
  const now = Date.now();
  const diffDays = Math.round((d.getTime() - now) / 86_400_000);
  if (diffDays === 0) return { text: 'Due today', overdue: false };
  if (diffDays > 0) return { text: `${diffDays} day${diffDays === 1 ? '' : 's'} left`, overdue: false };
  const past = Math.abs(diffDays);
  return { text: `${past} day${past === 1 ? '' : 's'} overdue`, overdue: true };
}

/** Turn an ENUM_VALUE into "Enum value" for prose. */
export function humanize(value: string): string {
  const lower = value.replace(/_/g, ' ').toLowerCase();
  return lower.charAt(0).toUpperCase() + lower.slice(1);
}

/** Turn an ENUM_VALUE into "Enum Value" (title case) — for compact labels. */
export function titleize(value: string): string {
  return value
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** First `n` characters of a hash/hex string, for provenance display. */
export function shortHash(hash: string, n = 12): string {
  if (!hash) return '—';
  return hash.length <= n ? hash : `${hash.slice(0, n)}…`;
}

/** A 0..1 fraction as a whole-number percentage string. */
export function pct(fraction: number): string {
  return `${Math.round(fraction * 100)}%`;
}

/** Signed points, e.g. "+12" / "−8" (uses a true minus glyph). */
export function signedPoints(points: number): string {
  const rounded = Math.round(points * 10) / 10;
  if (rounded > 0) return `+${rounded}`;
  if (rounded < 0) return `−${Math.abs(rounded)}`;
  return '0';
}
