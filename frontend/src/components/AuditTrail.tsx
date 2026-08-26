/**
 * Audit trail. Lazily fetches the decision log for a case — one row per pipeline
 * step — so every automated decision is traceable: which stage ran, which model
 * (or deterministic path) produced it, the decision, its confidence, latency and
 * the prompt hash when an LLM was involved. This is the accountability record;
 * it renders the backend's real fields (pipeline_stage / model_used / decision /
 * confidence / latency_ms / prompt_hash) with nothing invented.
 */

import { getAuditTrail } from '../lib/api';
import { useApi } from '../lib/useApi';
import type { Intent } from '../lib/status';
import { formatTime, pct, shortHash } from '../lib/format';
import { Badge, EmptyState, ErrorState, Loading } from './ui';
import { Cpu, Hash, ScrollText } from 'lucide-react';

function modelIntent(model: string): Intent {
  const m = model.toLowerCase();
  if (m.includes('deterministic') || m.includes('none') || m === '') return 'neu';
  return 'info';
}

export default function AuditTrail({ caseId }: { caseId: string }) {
  const { data, loading, error, reload } = useApi(() => getAuditTrail(caseId), caseId);

  if (loading) return <Loading label="Loading audit trail…" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return null;

  if (data.length === 0) {
    return (
      <section className="card">
        <div className="card__body">
          <EmptyState
            icon={<ScrollText size={26} />}
            title="No audit entries yet"
            hint="Decision-log entries appear here once the case has been analysed."
          />
        </div>
      </section>
    );
  }

  const ordered = [...data].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  );

  return (
    <section className="card" style={{ overflow: 'hidden' }}>
      <header className="card__header">
        <div>
          <div className="eyebrow">Accountability</div>
          <div className="section-title">Decision audit trail</div>
        </div>
        <span className="mono tnum" style={{ fontSize: 12, color: 'var(--muted)' }}>
          {data.length} step{data.length === 1 ? '' : 's'}
        </span>
      </header>
      <div className="scroll" style={{ overflowX: 'auto' }}>
        <table className="dtable">
          <thead>
            <tr>
              <th>Time</th>
              <th>Pipeline stage</th>
              <th>Model</th>
              <th>Decision</th>
              <th>Conf.</th>
              <th>Latency</th>
              <th>Prompt hash</th>
            </tr>
          </thead>
          <tbody>
            {ordered.map((e) => {
              return (
                <tr key={e.id}>
                  <td className="mono" style={{ whiteSpace: 'nowrap', color: 'var(--muted)' }}>{formatTime(e.timestamp)}</td>
                  <td style={{ fontWeight: 600, color: 'var(--ink)', whiteSpace: 'nowrap' }}>{e.pipeline_stage}</td>
                  <td>
                    <Badge intent={modelIntent(e.model_used)} mono icon={<Cpu size={11} />}>
                      {e.model_used || 'deterministic'}
                    </Badge>
                  </td>
                  <td style={{ maxWidth: 320 }}>{e.decision}</td>
                  <td className="mono tnum">{pct(e.confidence)}</td>
                  <td className="mono tnum" style={{ whiteSpace: 'nowrap' }}>{Math.round(e.latency_ms)} ms</td>
                  <td>
                    {e.prompt_hash ? (
                      <span className="prov" title={e.prompt_hash}>
                        <Hash size={11} /> {shortHash(e.prompt_hash, 10)}
                      </span>
                    ) : (
                      <span className="text-faint" style={{ fontSize: 12 }}>—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
