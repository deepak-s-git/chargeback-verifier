/**
 * Contradiction panel. Renders the deterministic detector's findings verbatim —
 * type, severity, description and the specific claims/evidence in conflict —
 * resolving claim ids to their real descriptions (no invented claim text). A
 * contradiction is a hard stop in this system: its presence forces mandatory
 * human review, so it is styled as a critical finding, never decoration.
 */

import type { Claim, Contradiction } from '../lib/types';
import { severityIntent } from '../lib/status';
import { titleize } from '../lib/format';
import { Badge, Pill } from './ui';
import { GitCompareArrows, Link2 } from 'lucide-react';

function ClaimRef({ id, claims }: { id: string; claims: Map<string, Claim> }) {
  const claim = claims.get(id);
  return (
    <div className="inset" style={{ padding: '10px 12px' }}>
      <div className="mono" style={{ fontSize: 11, color: 'var(--muted)' }}>{id}</div>
      <div style={{ fontSize: 13, color: 'var(--ink)', marginTop: 3 }}>
        {claim ? claim.description : <span className="text-faint">Referenced claim</span>}
      </div>
    </div>
  );
}

export default function ContradictionAlert({
  contradictions,
  claims,
}: {
  contradictions: Contradiction[];
  claims: Claim[];
}) {
  if (contradictions.length === 0) return null;
  const claimMap = new Map(claims.map((c) => [c.id, c]));

  return (
    <section className="card" style={{ borderColor: 'var(--crit-bd)' }}>
      <header className="card__header" style={{ background: 'var(--crit-bg)', borderColor: 'var(--crit-bd)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <GitCompareArrows size={17} style={{ color: 'var(--crit)' }} />
          <div>
            <div className="section-title" style={{ color: 'var(--crit)' }}>
              {contradictions.length} contradiction{contradictions.length === 1 ? '' : 's'} detected
            </div>
            <div style={{ fontSize: 12, color: 'var(--crit)' }}>
              Mandatory human review — the system will not compile a contest while evidence conflicts.
            </div>
          </div>
        </div>
      </header>
      <div className="card__body" style={{ display: 'grid', gap: 12 }}>
        {contradictions.map((c, i) => {
          const evidenceRefs = [c.evidence_a_id, c.evidence_b_id].filter((x): x is string => !!x);
          return (
            <div key={i} className="inset" style={{ padding: 14 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <Pill intent={severityIntent(c.severity)} dot>
                  {c.severity.toUpperCase()}
                </Pill>
                <Badge>{titleize(c.type)}</Badge>
              </div>
              <div style={{ fontSize: 13.5, color: 'var(--ink)' }}>{c.description}</div>

              {(c.claim_a_id || c.claim_b_id) && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 12 }}>
                  {c.claim_a_id && <ClaimRef id={c.claim_a_id} claims={claimMap} />}
                  {c.claim_b_id && <ClaimRef id={c.claim_b_id} claims={claimMap} />}
                </div>
              )}

              {evidenceRefs.length > 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
                  <Link2 size={13} style={{ color: 'var(--faint)' }} />
                  <span className="text-faint" style={{ fontSize: 11.5 }}>Conflicting evidence:</span>
                  {evidenceRefs.map((eid) => (
                    <Badge key={eid} mono>
                      {eid}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
