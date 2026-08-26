/**
 * Case workspace. The container for a selected case: it fetches the case (with
 * its evidence) and the analysis payload exactly once per case id, renders a
 * dense header (identity, amount, status, response deadline) and routes the tab
 * bar. Presentational tabs receive already-loaded data as props; the Package and
 * Audit tabs fetch their own data lazily by case id. Rendering is gated behind a
 * successful load of both case and analysis so no tab ever paints partial data.
 *
 * Mounted with `key={caseId}` by the shell, so switching cases remounts this
 * cleanly and resets tab + fetch state.
 */

import { useState } from 'react';
import type { ReactNode } from 'react';
import { getAnalysis, getCase } from '../lib/api';
import { useApi } from '../lib/useApi';
import { caseStatusIntent } from '../lib/status';
import { formatAmount, formatDeadline, titleize } from '../lib/format';
import { ErrorState, Loading, Pill } from './ui';
import CaseDashboard from './CaseDashboard';
import RequirementMatrix from './RequirementMatrix';
import ScoreBreakdown from './ScoreBreakdown';
import Timeline from './Timeline';
import EvidenceExplorer from './EvidenceExplorer';
import PackageViewer from './PackageViewer';
import AuditTrail from './AuditTrail';
import { Clock, Eye, Layers, ListChecks, PackageCheck, Scale, ScrollText } from 'lucide-react';

type TabKey = 'overview' | 'requirements' | 'score' | 'timeline' | 'evidence' | 'package' | 'audit';

interface TabDef {
  key: TabKey;
  label: string;
  icon: ReactNode;
  count?: number;
}

export default function CaseWorkspace({ caseId }: { caseId: string }) {
  const caseState = useApi(() => getCase(caseId), caseId);
  const analysisState = useApi(() => getAnalysis(caseId), caseId);
  const [tab, setTab] = useState<TabKey>('overview');

  const loading = caseState.loading || analysisState.loading;
  const error = caseState.error ?? analysisState.error;
  const reload = () => {
    caseState.reload();
    analysisState.reload();
  };

  if (loading) {
    return (
      <div style={{ display: 'grid', placeItems: 'center', height: '100%' }}>
        <Loading label="Analysing case…" />
      </div>
    );
  }
  if (error) {
    return (
      <div style={{ display: 'grid', placeItems: 'center', height: '100%' }}>
        <ErrorState message={error} onRetry={reload} />
      </div>
    );
  }
  if (!caseState.data || !analysisState.data) return null;

  const c = caseState.data;
  const analysis = analysisState.data;
  const deadline = formatDeadline(c.respond_by);

  const tabs: TabDef[] = [
    { key: 'overview', label: 'Overview', icon: <Eye size={15} /> },
    { key: 'requirements', label: 'Requirements', icon: <ListChecks size={15} />, count: analysis.requirements.length },
    { key: 'score', label: 'Score', icon: <Scale size={15} /> },
    { key: 'timeline', label: 'Timeline', icon: <Clock size={15} />, count: analysis.timeline.length },
    { key: 'evidence', label: 'Evidence', icon: <Layers size={15} />, count: c.evidence_items.length },
    { key: 'package', label: 'Package', icon: <PackageCheck size={15} /> },
    { key: 'audit', label: 'Audit', icon: <ScrollText size={15} /> },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minWidth: 0 }}>
      {/* Header */}
      <div style={{ padding: '20px 28px 0', borderBottom: '1px solid var(--hair)', background: 'var(--surface)' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 24, flexWrap: 'wrap' }}>
          <div style={{ minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <span className="mono" style={{ fontSize: 13, fontWeight: 650, color: 'var(--ink)' }}>{c.id}</span>
              <span className="badge badge--mono">{c.network === 'MASTERCARD' ? 'Mastercard' : 'Visa'}</span>
              <span className="badge">{c.reason_code}</span>
              <Pill intent={caseStatusIntent(c.status)} dot>{titleize(c.status)}</Pill>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 8, flexWrap: 'wrap' }}>
              <span className="text-muted" style={{ fontSize: 12.5 }}>{titleize(c.category)}</span>
              <span className="text-faint">·</span>
              <span className="text-muted" style={{ fontSize: 12.5 }}>{titleize(c.phase)} phase</span>
              <span className="text-faint">·</span>
              <span className="mono text-muted" style={{ fontSize: 12.5 }} title="Transaction ID">{c.transaction_id}</span>
            </div>
          </div>

          <div style={{ textAlign: 'right' }}>
            <div className="mono tnum" style={{ fontSize: 24, fontWeight: 700, color: 'var(--ink)' }}>
              {formatAmount(c.amount, c.currency)}
            </div>
            <div style={{ marginTop: 6, display: 'flex', justifyContent: 'flex-end' }}>
              <Pill intent={deadline.overdue ? 'crit' : 'neu'} icon={<Clock size={12} />}>
                {deadline.text}
              </Pill>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', marginTop: 18, overflowX: 'auto' }} className="scroll">
          {tabs.map((t) => (
            <button
              key={t.key}
              type="button"
              className={`tab${tab === t.key ? ' tab--active' : ''}`}
              onClick={() => setTab(t.key)}
            >
              {t.icon}
              {t.label}
              {typeof t.count === 'number' && <span className="tab__count">{t.count}</span>}
            </button>
          ))}
        </div>
      </div>

      {/* Body */}
      <div className="scroll" style={{ flex: 1, overflowY: 'auto', padding: 28, background: 'var(--canvas)' }}>
        <div style={{ maxWidth: 960, margin: '0 auto' }}>
          {tab === 'overview' && <CaseDashboard case={c} analysis={analysis} />}
          {tab === 'requirements' && (
            <RequirementMatrix requirements={analysis.requirements} ce30={analysis.ce30} network={c.network} />
          )}
          {tab === 'score' && (
            <ScoreBreakdown
              score={analysis.score}
              recommendation={analysis.recommendation}
              gateStatus={analysis.gate_status}
              gateReasons={analysis.gate_reasons}
            />
          )}
          {tab === 'timeline' && <Timeline events={analysis.timeline} />}
          {tab === 'evidence' && <EvidenceExplorer evidence={c.evidence_items} />}
          {tab === 'package' && <PackageViewer caseId={caseId} />}
          {tab === 'audit' && <AuditTrail caseId={caseId} />}
        </div>
      </div>
    </div>
  );
}
