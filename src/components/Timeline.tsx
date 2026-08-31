/**
 * Event timeline. Renders the reconstructed sequence of events (each tied to the
 * evidence item it came from) with any anomalies the deterministic checker
 * flagged — impossible ordering, suspicious gaps, future timestamps, etc. Those
 * anomalies are fraud/tamper signals, so they are surfaced inline on the event,
 * coloured by severity, never hidden.
 */

import type { TimelineEvent } from '../lib/types';
import { severityIntent } from '../lib/status';
import { formatDate, formatTime, titleize } from '../lib/format';
import { Badge, EmptyState, Pill } from './ui';
import { Clock, Globe, TriangleAlert, User } from 'lucide-react';

function EventNode({ event, last }: { event: TimelineEvent; last: boolean }) {
  const hasAnomaly = event.anomalies.length > 0;
  const dotColor = hasAnomaly ? 'var(--crit)' : 'var(--brand)';

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '132px 28px 1fr', gap: 0 }}>
      {/* Timestamp gutter */}
      <div style={{ textAlign: 'right', paddingRight: 14, paddingTop: 1 }}>
        <div className="mono" style={{ fontSize: 12, color: 'var(--ink-2)', fontWeight: 600 }}>
          {formatTime(event.timestamp)}
        </div>
        <div className="text-faint" style={{ fontSize: 11 }}>{formatDate(event.timestamp)}</div>
      </div>

      {/* Rail + dot */}
      <div style={{ position: 'relative', display: 'flex', justifyContent: 'center' }}>
        <div
          style={{
            width: 11,
            height: 11,
            borderRadius: 999,
            background: dotColor,
            marginTop: 3,
            zIndex: 1,
            boxShadow: '0 0 0 3px var(--surface)',
          }}
        />
        {!last && (
          <div
            style={{
              position: 'absolute',
              top: 12,
              bottom: -18,
              width: 2,
              background: 'var(--hair-strong)',
            }}
          />
        )}
      </div>

      {/* Content */}
      <div style={{ paddingBottom: 22, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          {event.event_type && <Badge intent="info">{titleize(event.event_type)}</Badge>}
          <span style={{ fontSize: 13.5, color: 'var(--ink)', fontWeight: 550 }}>{event.description}</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 6, flexWrap: 'wrap' }}>
          {event.actor && (
            <span className="text-muted" style={{ fontSize: 12, display: 'inline-flex', alignItems: 'center', gap: 5 }}>
              <User size={12} /> {event.actor}
            </span>
          )}
          {event.ip_address && (
            <span className="mono" style={{ fontSize: 12, color: 'var(--muted)', display: 'inline-flex', alignItems: 'center', gap: 5 }}>
              <Globe size={12} /> {event.ip_address}
            </span>
          )}
          <span className="mono" style={{ fontSize: 11, color: 'var(--faint)' }}>{event.evidence_id}</span>
        </div>

        {event.anomalies.map((a, i) => (
          <div key={i} className="banner banner--crit" style={{ marginTop: 8, padding: '9px 12px' }}>
            <TriangleAlert className="banner__icon" size={15} />
            <div style={{ minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontWeight: 650, fontSize: 12.5 }}>{titleize(a.type)}</span>
                <Pill intent={severityIntent(a.severity)} dot>{a.severity.toUpperCase()}</Pill>
              </div>
              <div className="banner__body" style={{ fontSize: 12.5 }}>{a.description}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Timeline({ events }: { events: TimelineEvent[] }) {
  if (events.length === 0) {
    return (
      <section className="card">
        <div className="card__body">
          <EmptyState
            icon={<Clock size={26} />}
            title="No timeline events"
            hint="No timestamped events could be reconstructed from the current evidence."
          />
        </div>
      </section>
    );
  }

  const ordered = [...events].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  );
  const anomalyCount = events.reduce((n, e) => n + e.anomalies.length, 0);

  return (
    <section className="card">
      <header className="card__header">
        <div>
          <div className="eyebrow">Reconstructed sequence</div>
          <div className="section-title">Event timeline</div>
        </div>
        {anomalyCount > 0 && (
          <Pill intent="crit" icon={<TriangleAlert size={13} />}>
            {anomalyCount} anomal{anomalyCount === 1 ? 'y' : 'ies'}
          </Pill>
        )}
      </header>
      <div className="card__body" style={{ paddingTop: 20 }}>
        {ordered.map((e, i) => (
          <EventNode key={e.id} event={e} last={i === ordered.length - 1} />
        ))}
      </div>
    </section>
  );
}
