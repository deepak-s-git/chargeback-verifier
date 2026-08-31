/**
 * Workbench UI primitives.
 *
 * Small, presentational building blocks that encode the design system's
 * semantics (intent → colour) so feature components stay declarative and every
 * status reads the same way across panels. No data fetching, no business logic.
 */

import type { CSSProperties, ReactNode } from 'react';
import { Inbox, RefreshCw, TriangleAlert } from 'lucide-react';
import type { Intent } from '../lib/status';

const PILL_CLASS: Record<Intent, string> = {
  pos: 'pill--pos',
  warn: 'pill--warn',
  neu: 'pill--neu',
  crit: 'pill--crit',
  info: 'pill--info',
};

const BADGE_CLASS: Record<Intent, string> = {
  pos: 'badge--pos',
  warn: 'badge--warn',
  neu: '',
  crit: 'badge--crit',
  info: 'badge--brand',
};

const METER_CLASS: Record<Intent, string> = {
  pos: 'meter__fill--pos',
  warn: 'meter__fill--warn',
  neu: 'meter__fill--neu',
  crit: 'meter__fill--crit',
  info: '',
};

export function Pill({
  intent,
  children,
  icon,
  dot = false,
}: {
  intent: Intent;
  children: ReactNode;
  icon?: ReactNode;
  dot?: boolean;
}) {
  return (
    <span className={`pill ${PILL_CLASS[intent]}${dot ? ' pill--dot' : ''}`}>
      {icon}
      {children}
    </span>
  );
}

export function Badge({
  intent = 'neu',
  mono = false,
  icon,
  children,
  title,
}: {
  intent?: Intent;
  mono?: boolean;
  icon?: ReactNode;
  children: ReactNode;
  title?: string;
}) {
  const cls = ['badge', BADGE_CLASS[intent], mono ? 'badge--mono' : ''].filter(Boolean).join(' ');
  return (
    <span className={cls} title={title}>
      {icon}
      {children}
    </span>
  );
}

export function Meter({ value, intent = 'neu' }: { value: number; intent?: Intent }) {
  const width = `${Math.max(0, Math.min(1, value)) * 100}%`;
  return (
    <div className="meter">
      <div className={`meter__fill ${METER_CLASS[intent]}`} style={{ width }} />
    </div>
  );
}

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="empty" role="status" aria-live="polite">
      <div className="spinner" />
      <div className="text-muted">{label}</div>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="empty" role="alert">
      <TriangleAlert className="empty__icon" size={26} />
      <div className="text-ink" style={{ fontWeight: 650 }}>
        Couldn’t load this
      </div>
      <div className="text-muted" style={{ maxWidth: 380 }}>
        {message}
      </div>
      {onRetry && (
        <button className="btn btn--sm" onClick={onRetry} style={{ marginTop: 4 }}>
          <RefreshCw size={14} />
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  hint,
}: {
  icon?: ReactNode;
  title: string;
  hint?: ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty__icon">{icon ?? <Inbox size={26} />}</div>
      <div className="text-ink" style={{ fontWeight: 650 }}>
        {title}
      </div>
      {hint && (
        <div className="text-muted" style={{ maxWidth: 400 }}>
          {hint}
        </div>
      )}
    </div>
  );
}

/** A titled panel with the standard card chrome. */
export function Panel({
  title,
  eyebrow,
  right,
  children,
  bodyStyle,
}: {
  title?: ReactNode;
  eyebrow?: ReactNode;
  right?: ReactNode;
  children: ReactNode;
  bodyStyle?: CSSProperties;
}) {
  return (
    <section className="card">
      {(title || right) && (
        <header className="card__header">
          <div>
            {eyebrow && <div className="eyebrow">{eyebrow}</div>}
            {title && <div className="section-title">{title}</div>}
          </div>
          {right}
        </header>
      )}
      <div className="card__body" style={bodyStyle}>
        {children}
      </div>
    </section>
  );
}
