/**
 * Case dashboard — the at-a-glance verdict for a case. It states the engine's
 * recommendation, the evidence score, the human-review gate, and any hard risk
 * flags (prompt injection in evidence, contradictions) up top, then summarises
 * requirement coverage, claim status and real evidence counts. Every number is
 * read straight from the analysis payload or the case's own evidence items —
 * there are no derived "win probability" or cost figures, because the engine
 * does not compute them and inventing them would violate the platform's core
 * rule against unsupported claims.
 */

import type { ReactNode } from 'react';
import type { CaseAnalysis, ClaimStatus, DisputeCase, RequirementStatus } from '../lib/types';
import type { Intent } from '../lib/status';
import {
  claimIntent,
  gateIntent,
  recommendationIntent,
  requirementIntent,
  scoreIntent,
} from '../lib/status';
import { titleize } from '../lib/format';
import { Panel, Pill } from './ui';
import ContradictionAlert from './ContradictionAlert';
import {
  FileText,
  Layers,
  ListChecks,
  Scale,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react';

const INTENT_COLOR: Record<Intent, string> = {
  pos: 'var(--pos)',
  warn: 'var(--warn)',
  neu: 'var(--neu)',
  crit: 'var(--crit)',
  info: 'var(--info)',
};

const REQ_ORDER: RequirementStatus[] = [
  'SATISFIED',
  'PARTIALLY_SATISFIED',
  'MISSING',
  'CONTRADICTED',
  'NOT_APPLICABLE',
];
const CLAIM_ORDER: ClaimStatus[] = ['VERIFIED', 'NEEDS_REVIEW', 'BLOCKED', 'DRAFT'];

function StatTile({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: ReactNode;
}) {
  return (
    <div className="card card--pad" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div className="eyebrow">{label}</div>
      {children}
      {hint && <div className="text-muted" style={{ fontSize: 12 }}>{hint}</div>}
    </div>
  );
}

function CountRow<T extends string>({
  order,
  counts,
  intentOf,
}: {
  order: T[];
  counts: Record<string, number>;
  intentOf: (s: T) => Intent;
}) {
  const present = order.filter((s) => (counts[s] ?? 0) > 0);
  if (present.length === 0) {
    return <div className="text-muted" style={{ fontSize: 13 }}>None.</div>;
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {present.map((s) => (
        <div key={s} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
          <Pill intent={intentOf(s)} dot>{titleize(s)}</Pill>
          <span className="mono tnum" style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)' }}>
            {counts[s]}
          </span>
        </div>
      ))}
    </div>
  );
}

function tally<T extends string>(items: { status: T }[]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const it of items) out[it.status] = (out[it.status] ?? 0) + 1;
  return out;
}

export default function CaseDashboard({
  case: c,
  analysis,
}: {
  case: DisputeCase;
  analysis: CaseAnalysis;
}) {
  const scoreColor = INTENT_COLOR[scoreIntent(analysis.score.total_score)];
  const factCount = c.evidence_items.reduce((n, e) => n + e.extracted_facts.length, 0);
  const reqCounts = tally(analysis.requirements);
  const claimCounts = tally(analysis.claims);

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      {/* Verdict tiles */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        <StatTile label="Recommendation" hint="What the evidence supports doing.">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Pill intent={recommendationIntent(analysis.recommendation)} icon={<ShieldCheck size={13} />}>
              {analysis.recommendation}
            </Pill>
          </div>
        </StatTile>

        <StatTile label="Evidence score" hint="Deterministic strength of defense (0–100).">
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
            <span className="mono tnum" style={{ fontSize: 30, fontWeight: 700, color: scoreColor, lineHeight: 1 }}>
              {Math.round(analysis.score.total_score)}
            </span>
            <span className="text-faint mono" style={{ fontSize: 13 }}>/ 100</span>
          </div>
        </StatTile>

        <StatTile label="Review gate" hint="DisputeShield drafts only — a human decides.">
          <div>
            <Pill intent={gateIntent(analysis.gate_status)} icon={<Scale size={13} />}>
              {titleize(analysis.gate_status)}
            </Pill>
          </div>
        </StatTile>
      </div>

      {/* Prompt-injection flag (defense showcase) */}
      {analysis.injection_detected && (
        <div className="banner banner--crit">
          <ShieldAlert className="banner__icon" size={18} />
          <div style={{ minWidth: 0 }}>
            <div className="banner__title">Prompt injection detected in evidence</div>
            <div className="banner__body">
              Suspicious instruction-like content was found in the submitted evidence. It has been
              flagged and is treated as untrusted data — never executed — and this case is forced to
              mandatory human review.
            </div>
            {analysis.injection_patterns.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                {analysis.injection_patterns.map((p, i) => (
                  <code
                    key={i}
                    className="mono"
                    style={{
                      fontSize: 11,
                      background: 'var(--surface)',
                      border: '1px solid var(--crit-bd)',
                      color: 'var(--crit)',
                      borderRadius: 'var(--r-xs)',
                      padding: '2px 7px',
                    }}
                  >
                    {p}
                  </code>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Contradictions (hard stop) */}
      <ContradictionAlert contradictions={analysis.contradictions} claims={analysis.claims} />

      {/* Coverage + claims + evidence */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <Panel eyebrow="Rule engine" title="Requirement coverage" right={<ListChecks size={16} style={{ color: 'var(--faint)' }} />}>
          <CountRow<RequirementStatus>
            order={REQ_ORDER}
            counts={reqCounts}
            intentOf={requirementIntent}
          />
        </Panel>

        <Panel eyebrow="Assertions" title="Claim status" right={<FileText size={16} style={{ color: 'var(--faint)' }} />}>
          <CountRow<ClaimStatus> order={CLAIM_ORDER} counts={claimCounts} intentOf={claimIntent} />
        </Panel>
      </div>

      <Panel eyebrow="Intake" title="Evidence on file" right={<Layers size={16} style={{ color: 'var(--faint)' }} />}>
        <div style={{ display: 'flex', gap: 40, flexWrap: 'wrap' }}>
          <div>
            <div className="mono tnum" style={{ fontSize: 26, fontWeight: 700, color: 'var(--ink)' }}>
              {c.evidence_items.length}
            </div>
            <div className="text-muted" style={{ fontSize: 12 }}>evidence item{c.evidence_items.length === 1 ? '' : 's'}</div>
          </div>
          <div>
            <div className="mono tnum" style={{ fontSize: 26, fontWeight: 700, color: 'var(--ink)' }}>
              {factCount}
            </div>
            <div className="text-muted" style={{ fontSize: 12 }}>extracted fact{factCount === 1 ? '' : 's'}</div>
          </div>
          {analysis.ce30 && (
            <div>
              <Pill intent={analysis.ce30.qualified ? 'pos' : 'neu'}>
                CE 3.0 {analysis.ce30.qualified ? 'qualified' : 'not qualified'}
              </Pill>
              <div className="text-muted" style={{ fontSize: 12, marginTop: 6 }}>
                Visa compelling-evidence prior-transaction test
              </div>
            </div>
          )}
        </div>
      </Panel>
    </div>
  );
}
