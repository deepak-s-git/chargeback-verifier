/**
 * Case navigation list for the command rail (dark surface). Purely
 * prop-driven — no fetching, no mock. Renders each dispute as a compact,
 * scannable row: short id, transaction reference, network, live status and
 * amount, with the selected case accented.
 */

import type { DisputeCase } from '../lib/types';
import { caseStatusIntent, type Intent } from '../lib/status';
import { formatAmount, titleize } from '../lib/format';
import { EmptyState } from './ui';
import { Layers } from 'lucide-react';

/** Brighter dot colours tuned for the dark rail. */
const DOT: Record<Intent, string> = {
  pos: '#34d399',
  warn: '#fbbf24',
  neu: '#9598a3',
  crit: '#f87171',
  info: '#60a5fa',
};

function networkLabel(network: DisputeCase['network']): string {
  return network === 'MASTERCARD' ? 'MC' : 'VISA';
}

export default function CaseList({
  cases,
  selectedId,
  onSelect,
}: {
  cases: DisputeCase[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  if (cases.length === 0) {
    return (
      <div style={{ padding: '8px 4px' }}>
        <EmptyState
          icon={<Layers size={24} />}
          title="No cases yet"
          hint="Create a case or load the demo set to begin."
        />
      </div>
    );
  }

  return (
    <div className="scroll-rail" style={{ overflowY: 'auto', paddingRight: 2 }}>
      {cases.map((c) => {
        const intent = caseStatusIntent(c.status);
        const active = c.id === selectedId;
        return (
          <button
            key={c.id}
            type="button"
            className={`nav-item${active ? ' nav-item--active' : ''}`}
            onClick={() => onSelect(c.id)}
            aria-current={active}
          >
            <div className="nav-item__top">
              <span className="nav-item__id">{c.id}</span>
              <span className="rail-badge">{networkLabel(c.network)}</span>
            </div>
            <div className="nav-item__title" title={c.transaction_id}>
              {c.dispute_id || c.transaction_id}
            </div>
            <div className="nav-item__meta">
              <span
                className="status-dot"
                style={{ background: DOT[intent] }}
                aria-hidden
              />
              <span style={{ fontSize: 11.5, color: 'var(--rail-muted)' }}>
                {titleize(c.status)}
              </span>
              <span className="rail-amount">{formatAmount(c.amount, c.currency)}</span>
            </div>
          </button>
        );
      })}
    </div>
  );
}
