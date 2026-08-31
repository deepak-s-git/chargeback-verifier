/**
 * Package viewer. Lazily fetches the compiled, review-gated evidence package for
 * a case and presents it the way a reviewer needs it: the disposition, the exact
 * reasons human review is required, each claim's status (with block reasons for
 * anything unsupported), and the draft network submission.
 *
 * The network submission is emphatically a DRAFT. DisputeShield never transmits
 * to the card network — it compiles a package for a human to approve — so the
 * viewer states that plainly and the export is a local file, not a submission.
 */

import type { Claim } from '../lib/types';
import { getPackage } from '../lib/api';
import { useApi } from '../lib/useApi';
import { claimIntent, recommendationIntent } from '../lib/status';
import { formatDateTime, titleize } from '../lib/format';
import { Badge, ErrorState, Loading, Panel, Pill } from './ui';
import { Ban, CircleCheck, Download, Gavel, Lock, PackageCheck } from 'lucide-react';

function ClaimCard({ claim }: { claim: Claim }) {
  const blocked = claim.status === 'BLOCKED';
  return (
    <div className="inset" style={{ padding: 14, borderColor: blocked ? 'var(--crit-bd)' : undefined }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 13.5, color: 'var(--ink)', fontWeight: 550 }}>{claim.description}</div>
          <div className="mono" style={{ fontSize: 11, color: 'var(--faint)', marginTop: 4 }}>{claim.id}</div>
        </div>
        <Pill intent={claimIntent(claim.status)} dot>{titleize(claim.status)}</Pill>
      </div>

      {claim.block_reason && (
        <div style={{ display: 'flex', gap: 7, alignItems: 'flex-start', marginTop: 10, color: 'var(--crit)' }}>
          <Ban size={13} style={{ marginTop: 2, flex: 'none' }} />
          <span style={{ fontSize: 12.5 }}>{claim.block_reason}</span>
        </div>
      )}

      {claim.supporting_evidence_ids.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center', marginTop: 10 }}>
          <span className="text-faint" style={{ fontSize: 11 }}>Supported by</span>
          {claim.supporting_evidence_ids.map((id) => (
            <Badge key={id} mono>{id}</Badge>
          ))}
        </div>
      )}
    </div>
  );
}

export default function PackageViewer({ caseId }: { caseId: string }) {
  const { data, loading, error, reload } = useApi(() => getPackage(caseId), caseId);

  if (loading) return <Loading label="Compiling package…" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return null;

  const submission = data.network_submission;
  const action =
    submission && typeof submission.action === 'string' ? submission.action : null;

  const verified = data.claims.filter((c) => c.status === 'VERIFIED');
  const blocked = data.claims.filter((c) => c.status === 'BLOCKED');
  const other = data.claims.filter((c) => c.status !== 'VERIFIED' && c.status !== 'BLOCKED');
  const orderedClaims = [...verified, ...blocked, ...other];

  const download = () => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${data.case_id}-package.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <Panel
        eyebrow="Compiled for human review"
        title="Evidence package"
        right={
          <button className="btn btn--sm" onClick={download}>
            <Download size={14} /> Export JSON
          </button>
        }
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          {data.recommendation && (
            <Pill intent={recommendationIntent(data.recommendation)} icon={<PackageCheck size={13} />}>
              {data.recommendation}
            </Pill>
          )}
          {data.score && (
            <span className="mono tnum" style={{ fontSize: 13, color: 'var(--muted)' }}>
              Score {Math.round(data.score.total_score)}/100
            </span>
          )}
          <span className="text-faint" style={{ fontSize: 11.5, marginLeft: 'auto' }}>
            Generated {formatDateTime(data.generated_at)}
          </span>
        </div>
      </Panel>

      {/* Review gate reasons */}
      <div className={`banner ${data.review_required ? 'banner--warn' : 'banner--pos'}`}>
        {data.review_required ? (
          <Gavel className="banner__icon" size={17} />
        ) : (
          <CircleCheck className="banner__icon" size={17} />
        )}
        <div>
          <div className="banner__title">
            {data.review_required ? 'Human review required before use' : 'No blocking review conditions'}
          </div>
          {data.review_reasons.length > 0 ? (
            <ul style={{ margin: '6px 0 0', paddingLeft: 18 }}>
              {data.review_reasons.map((r, i) => (
                <li key={i} className="banner__body" style={{ marginTop: 2 }}>{r}</li>
              ))}
            </ul>
          ) : (
            <div className="banner__body">
              This package still requires a human to approve before anything is sent anywhere.
            </div>
          )}
        </div>
      </div>

      {/* Claims */}
      <Panel eyebrow="Assertions in the package" title={`Claims (${data.claims.length})`}>
        {orderedClaims.length === 0 ? (
          <div className="text-muted" style={{ fontSize: 13 }}>No claims were compiled for this case.</div>
        ) : (
          <div style={{ display: 'grid', gap: 10 }}>
            {orderedClaims.map((c) => (
              <ClaimCard key={c.id} claim={c} />
            ))}
          </div>
        )}
      </Panel>

      {/* Draft network submission */}
      <Panel
        eyebrow="Draft output"
        title="Network submission"
        right={<Pill intent="neu" icon={<Lock size={13} />}>{action ? titleize(action) : 'Draft'}</Pill>}
      >
        <div className="banner banner--neu" style={{ marginBottom: 12 }}>
          <Lock className="banner__icon" size={16} />
          <div className="banner__body" style={{ color: 'var(--ink-2)' }}>
            Draft only — DisputeShield never submits to the card network. This payload is prepared for
            a human to review and file manually.
          </div>
        </div>
        {submission ? (
          <pre className="raw scroll">{JSON.stringify(submission, null, 2)}</pre>
        ) : (
          <div className="text-muted" style={{ fontSize: 13 }}>
            No submission draft was generated — the evidence does not support contesting.
          </div>
        )}
      </Panel>
    </div>
  );
}
