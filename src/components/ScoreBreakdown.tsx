/**
 * Score breakdown. Shows the deterministic 0–100 evidence score, the resulting
 * recommendation and the human-review gate, then every scoring factor with its
 * signed contribution and the evidence it draws on.
 *
 * It deliberately shows ONLY what the engine computes. The previous version
 * fabricated a "win probability", arbitration fees and an expected value — none
 * of which the backend produces. Inventing those numbers in the UI is the same
 * class of error the whole product exists to prevent, so they are gone.
 */

import type { EvidenceScore, GateStatus, Recommendation } from '../lib/types';
import {
  gateIntent,
  recommendationIntent,
  scoreIntent,
  scoringFactorIntent,
  type Intent,
} from '../lib/status';
import { signedPoints, titleize } from '../lib/format';
import { Panel, Pill } from './ui';
import { CircleCheck, CircleDashed, OctagonAlert, Scale, ShieldCheck } from 'lucide-react';

const INTENT_COLOR: Record<Intent, string> = {
  pos: 'var(--pos)',
  warn: 'var(--warn)',
  neu: 'var(--neu)',
  crit: 'var(--crit)',
  info: 'var(--info)',
};

const REC_BLURB: Record<Recommendation, string> = {
  CONTEST: 'Evidence supports contesting this dispute.',
  REVIEW: 'Mixed signals — a human should review before deciding.',
  INSUFFICIENT: 'Not enough grounded evidence to contest.',
  ABSTAIN: 'Insufficient evidence; the system abstains rather than guess.',
};

function Gauge({ score }: { score: number }) {
  const clamped = Math.max(0, Math.min(100, score));
  const R = 54;
  const C = 2 * Math.PI * R;
  const offset = C * (1 - clamped / 100);
  const color = INTENT_COLOR[scoreIntent(clamped)];
  return (
    <div style={{ position: 'relative', width: 140, height: 140 }}>
      <svg width={140} height={140} viewBox="0 0 140 140">
        <circle cx={70} cy={70} r={R} fill="none" stroke="var(--surface-inset)" strokeWidth={12} />
        <circle
          cx={70}
          cy={70}
          r={R}
          fill="none"
          stroke={color}
          strokeWidth={12}
          strokeLinecap="round"
          strokeDasharray={C}
          strokeDashoffset={offset}
          transform="rotate(-90 70 70)"
          style={{ transition: 'stroke-dashoffset 0.5s ease' }}
        />
      </svg>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <div className="mono tnum" style={{ fontSize: 34, fontWeight: 700, color: 'var(--ink)', lineHeight: 1 }}>
          {Math.round(clamped)}
        </div>
        <div className="eyebrow" style={{ marginTop: 2 }}>/ 100</div>
      </div>
    </div>
  );
}

function FactorIcon({ type }: { type: EvidenceScore['factors'][number]['type'] }) {
  if (type === 'POSITIVE') return <CircleCheck size={16} style={{ color: 'var(--pos)' }} />;
  if (type === 'NEGATIVE') return <OctagonAlert size={16} style={{ color: 'var(--crit)' }} />;
  return <CircleDashed size={16} style={{ color: 'var(--faint)' }} />;
}

export default function ScoreBreakdown({
  score,
  recommendation,
  gateStatus,
  gateReasons,
}: {
  score: EvidenceScore;
  recommendation: Recommendation;
  gateStatus: GateStatus;
  gateReasons: string[];
}) {
  const factors = [...score.factors].sort((a, b) => b.points - a.points);

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(240px, 320px) 1fr', gap: 16 }}>
        <Panel eyebrow="Evidence score" title="Strength of defense">
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
            <Gauge score={score.total_score} />
            <Pill intent={recommendationIntent(recommendation)} icon={<ShieldCheck size={13} />}>
              {recommendation}
            </Pill>
            <p className="text-muted" style={{ textAlign: 'center', margin: 0, fontSize: 12.5 }}>
              {REC_BLURB[recommendation]}
            </p>
          </div>
        </Panel>

        <Panel eyebrow="Human-review gate" title="Disposition" right={<Scale size={16} style={{ color: 'var(--faint)' }} />}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div>
              <Pill intent={gateIntent(gateStatus)} dot>
                {titleize(gateStatus)}
              </Pill>
            </div>
            <ul style={{ margin: 0, paddingLeft: 18, display: 'grid', gap: 6 }}>
              {gateReasons.length > 0 ? (
                gateReasons.map((r, i) => (
                  <li key={i} style={{ fontSize: 13, color: 'var(--ink-2)' }}>
                    {r}
                  </li>
                ))
              ) : (
                <li className="text-muted" style={{ fontSize: 13 }}>No gate notes.</li>
              )}
            </ul>
            <p className="text-faint" style={{ margin: 0, fontSize: 11.5 }}>
              DisputeShield never submits to the network — it compiles a draft for a human to sign off.
            </p>
          </div>
        </Panel>
      </div>

      <Panel eyebrow="Contributions" title={`Scoring factors (${factors.length})`}>
        {factors.length === 0 ? (
          <div className="text-muted" style={{ fontSize: 13 }}>No factors contributed to this score.</div>
        ) : (
          <div style={{ display: 'grid', gap: 2 }}>
            {factors.map((f, i) => (
              <div
                key={i}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '20px 1fr auto',
                  gap: 12,
                  alignItems: 'start',
                  padding: '11px 4px',
                  borderBottom: i < factors.length - 1 ? '1px solid var(--hair)' : 'none',
                }}
              >
                <div style={{ paddingTop: 1 }}>
                  <FactorIcon type={f.type} />
                </div>
                <div>
                  <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--ink)' }}>{f.name}</div>
                  <div className="text-muted" style={{ fontSize: 12.5, marginTop: 2 }}>{f.description}</div>
                  {f.evidence_ids.length > 0 && (
                    <div className="mono" style={{ fontSize: 11, color: 'var(--faint)', marginTop: 4 }}>
                      {f.evidence_ids.join(' · ')}
                    </div>
                  )}
                </div>
                <div
                  className="mono tnum"
                  style={{
                    fontSize: 14,
                    fontWeight: 700,
                    color: INTENT_COLOR[scoringFactorIntent(f.type)],
                    whiteSpace: 'nowrap',
                  }}
                >
                  {signedPoints(f.points)}
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
