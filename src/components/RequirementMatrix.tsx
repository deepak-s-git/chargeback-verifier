/**
 * Requirement matrix. For the case's network + reason code, the deterministic
 * rule engine emits the dispute requirements and, per requirement, how well the
 * extracted evidence covers it (satisfied / partial / missing / contradicted),
 * which fact types are present vs. absent, and the rule citation.
 *
 * This is the heart of the "which claims are actually supported" question, so it
 * shows the engine's finding verbatim — coverage, fact types and source
 * reference all come from the payload; nothing is inferred in the UI.
 */

import type { ReactNode } from 'react';
import type { CardNetwork, CE30Result, Requirement, RequirementStatus } from '../lib/types';
import { requirementIntent } from '../lib/status';
import { pct, titleize } from '../lib/format';
import { Badge, Meter, Panel, Pill } from './ui';
import {
  Ban,
  CircleCheck,
  CircleDashed,
  GitCompareArrows,
  Landmark,
  ListChecks,
  Zap,
} from 'lucide-react';

const STATUS_ICON: Record<RequirementStatus, ReactNode> = {
  SATISFIED: <CircleCheck size={15} style={{ color: 'var(--pos)' }} />,
  PARTIALLY_SATISFIED: <CircleDashed size={15} style={{ color: 'var(--warn)' }} />,
  MISSING: <CircleDashed size={15} style={{ color: 'var(--faint)' }} />,
  CONTRADICTED: <GitCompareArrows size={15} style={{ color: 'var(--crit)' }} />,
  NOT_APPLICABLE: <Ban size={15} style={{ color: 'var(--faint)' }} />,
};

function coverageIntent(status: RequirementStatus) {
  return requirementIntent(status);
}

function RequirementRow({ req }: { req: Requirement }) {
  const intent = requirementIntent(req.status);
  return (
    <div style={{ padding: '16px 18px', borderBottom: '1px solid var(--hair)' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', minWidth: 0 }}>
          <div style={{ paddingTop: 2 }}>{STATUS_ICON[req.status]}</div>
          <div style={{ minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 14, fontWeight: 650, color: 'var(--ink)' }}>{req.name}</span>
              <Badge>{titleize(req.strength)}</Badge>
              {req.is_auto_win && (
                <Badge intent="pos" icon={<Zap size={11} />}>
                  Auto-win eligible
                </Badge>
              )}
            </div>
            <div className="text-muted" style={{ fontSize: 12.5, marginTop: 3 }}>
              {req.description}
            </div>
          </div>
        </div>
        <Pill intent={intent} dot>
          {titleize(req.status)}
        </Pill>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '160px 1fr', gap: 16, marginTop: 14, alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="mono tnum" style={{ fontSize: 12, color: 'var(--muted)', width: 34 }}>{pct(req.coverage)}</span>
          <div style={{ flex: 1 }}>
            <Meter value={req.coverage} intent={coverageIntent(req.status)} />
          </div>
        </div>
        <div className="mono" style={{ fontSize: 11, color: 'var(--faint)' }}>
          {req.source_reference}
        </div>
      </div>

      {(req.satisfied_fact_types.length > 0 || req.missing_fact_types.length > 0) && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 12 }}>
          {req.satisfied_fact_types.map((t) => (
            <Badge key={`s-${t}`} intent="pos" icon={<CircleCheck size={11} />}>
              {titleize(t)}
            </Badge>
          ))}
          {req.missing_fact_types.map((t) => (
            <Badge key={`m-${t}`} icon={<CircleDashed size={11} />} title="Not found in evidence">
              {titleize(t)}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

function CE30Panel({ ce30 }: { ce30: CE30Result }) {
  return (
    <Panel
      eyebrow="Visa Compelling Evidence 3.0"
      title="Prior-transaction match"
      right={
        <Pill intent={ce30.qualified ? 'pos' : 'neu'} icon={<Landmark size={13} />}>
          {ce30.qualified ? 'Qualified' : 'Not qualified'}
        </Pill>
      }
    >
      <div style={{ display: 'grid', gap: 14 }}>
        <p className="text-body" style={{ margin: 0, fontSize: 13 }}>{ce30.reason}</p>

        {ce30.matching_elements.length > 0 && (
          <div>
            <div className="eyebrow" style={{ marginBottom: 6 }}>Matching anchors</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {ce30.matching_elements.map((el) => (
                <Badge key={el} intent="pos">{titleize(el)}</Badge>
              ))}
            </div>
          </div>
        )}

        {ce30.qualifying_details.length > 0 && (
          <div>
            <div className="eyebrow" style={{ marginBottom: 6 }}>
              Qualifying prior transactions ({ce30.qualifying_details.length})
            </div>
            <div className="inset" style={{ overflow: 'hidden' }}>
              <table className="dtable">
                <thead>
                  <tr>
                    <th>Evidence</th>
                    <th>Days before dispute</th>
                    <th>Matching anchors</th>
                  </tr>
                </thead>
                <tbody>
                  {ce30.qualifying_details.map((q) => (
                    <tr key={q.evidence_id}>
                      <td className="mono">{q.evidence_id}</td>
                      <td className="mono tnum">{q.days_before_dispute}</td>
                      <td>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                          {q.matching_elements.map((el) => (
                            <Badge key={el}>{titleize(el)}</Badge>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </Panel>
  );
}

export default function RequirementMatrix({
  requirements,
  ce30,
  network,
}: {
  requirements: Requirement[];
  ce30: CE30Result | null;
  network: CardNetwork;
}) {
  const satisfied = requirements.filter((r) => r.status === 'SATISFIED').length;

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <Panel
        eyebrow={`${network === 'MASTERCARD' ? 'Mastercard' : 'Visa'} dispute requirements`}
        title="Requirement coverage"
        right={
          <span className="mono tnum" style={{ fontSize: 12.5, color: 'var(--muted)' }}>
            {satisfied}/{requirements.length} satisfied
          </span>
        }
        bodyStyle={{ padding: 0 }}
      >
        {requirements.length === 0 ? (
          <div className="empty">
            <ListChecks className="empty__icon" size={26} />
            <div className="text-ink" style={{ fontWeight: 650 }}>No requirements to evaluate</div>
            <div className="text-muted" style={{ maxWidth: 420 }}>
              This network and reason code have no rule definition, so the engine abstains rather
              than score an unmapped dispute.
            </div>
          </div>
        ) : (
          <div>
            {requirements.map((r) => (
              <RequirementRow key={r.id} req={r} />
            ))}
          </div>
        )}
      </Panel>

      {ce30 && <CE30Panel ce30={ce30} />}
    </div>
  );
}
