/**
 * Evidence explorer. A master/detail view over the case's ingested evidence:
 * pick an item on the left, inspect its extracted facts on the right. Every fact
 * shows how it was extracted (deterministic / regex / OCR / LLM) and its
 * provenance hash, so an analyst can trace any value back to the source bytes —
 * the traceability the whole platform is built on. Raw content is shown as-is,
 * as untrusted text, never interpreted as instructions.
 */

import { useState } from 'react';
import type { EvidenceItem, ExtractionMethod } from '../lib/types';
import type { Intent } from '../lib/status';
import { formatDateTime, pct, shortHash, titleize } from '../lib/format';
import { Badge, EmptyState, Meter } from './ui';
import { Braces, FileText, Hash, Inbox, MapPin } from 'lucide-react';

const METHOD_INTENT: Record<ExtractionMethod, Intent> = {
  DETERMINISTIC: 'pos',
  REGEX: 'neu',
  OCR: 'neu',
  LLM: 'warn',
};

function confidenceIntent(c: number): Intent {
  if (c >= 0.8) return 'pos';
  if (c >= 0.5) return 'warn';
  return 'crit';
}

function EvidenceDetail({ item }: { item: EvidenceItem }) {
  return (
    <div className="scroll" style={{ overflowY: 'auto', height: '100%' }}>
      <div style={{ padding: 18 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span className="mono" style={{ fontSize: 13, fontWeight: 650, color: 'var(--ink)' }}>{item.id}</span>
          <Badge intent="info">{titleize(item.semantic_type)}</Badge>
          <Badge>{titleize(item.source_type)}</Badge>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 12, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span className="eyebrow">Confidence</span>
            <div style={{ width: 90 }}><Meter value={item.confidence} intent={confidenceIntent(item.confidence)} /></div>
            <span className="mono tnum" style={{ fontSize: 12, color: 'var(--muted)' }}>{pct(item.confidence)}</span>
          </div>
          <span className="text-faint" style={{ fontSize: 11.5 }}>Ingested {formatDateTime(item.created_at)}</span>
        </div>

        {item.file_path && (
          <div className="prov" style={{ marginTop: 12 }}>
            <FileText size={12} /> {item.file_path}
          </div>
        )}

        {/* Extracted facts */}
        <div style={{ marginTop: 20 }}>
          <div className="eyebrow" style={{ marginBottom: 8 }}>
            Extracted facts ({item.extracted_facts.length})
          </div>
          {item.extracted_facts.length === 0 ? (
            <div className="inset" style={{ padding: 14 }}>
              <span className="text-muted" style={{ fontSize: 13 }}>No facts were extracted from this item.</span>
            </div>
          ) : (
            <div className="inset" style={{ overflow: 'hidden' }}>
              <table className="dtable">
                <thead>
                  <tr>
                    <th>Fact</th>
                    <th>Value</th>
                    <th>Method</th>
                    <th>Conf.</th>
                    <th>Provenance</th>
                  </tr>
                </thead>
                <tbody>
                  {item.extracted_facts.map((f, i) => (
                    <tr key={i}>
                      <td style={{ whiteSpace: 'nowrap' }}>{titleize(f.type)}</td>
                      <td className="mono" style={{ maxWidth: 220, wordBreak: 'break-word' }}>{f.value}</td>
                      <td><Badge intent={METHOD_INTENT[f.extraction_method]}>{titleize(f.extraction_method)}</Badge></td>
                      <td className="mono tnum">{pct(f.confidence)}</td>
                      <td>
                        <span
                          className="prov"
                          title={`${f.provenance.source_file} · ${f.provenance.source_location}\n${f.provenance.content_hash}`}
                        >
                          <Hash size={11} /> {shortHash(f.provenance.content_hash, 10)}
                        </span>
                        {f.provenance.source_location && (
                          <div className="text-faint" style={{ fontSize: 10.5, marginTop: 3, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                            <MapPin size={10} /> {f.provenance.source_location}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Raw content — untrusted */}
        {item.raw_content && (
          <div style={{ marginTop: 20 }}>
            <div className="eyebrow" style={{ marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Braces size={12} /> Raw content
            </div>
            <pre className="raw scroll">{item.raw_content}</pre>
          </div>
        )}
      </div>
    </div>
  );
}

export default function EvidenceExplorer({ evidence }: { evidence: EvidenceItem[] }) {
  const [selectedId, setSelectedId] = useState<string | null>(evidence[0]?.id ?? null);

  if (evidence.length === 0) {
    return (
      <section className="card">
        <div className="card__body">
          <EmptyState
            icon={<Inbox size={26} />}
            title="No evidence ingested"
            hint="Add evidence from the case's intake, or load the demo set, then re-run analysis."
          />
        </div>
      </section>
    );
  }

  const selected = evidence.find((e) => e.id === selectedId) ?? evidence[0];

  return (
    <section className="card" style={{ overflow: 'hidden' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', height: 560 }}>
        {/* Master list */}
        <div className="scroll" style={{ overflowY: 'auto', borderRight: '1px solid var(--hair)', background: 'var(--surface-2)' }}>
          {evidence.map((item) => {
            const active = item.id === selected.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setSelectedId(item.id)}
                style={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'left',
                  padding: '12px 14px',
                  border: 'none',
                  borderBottom: '1px solid var(--hair)',
                  borderLeft: active ? '3px solid var(--brand)' : '3px solid transparent',
                  background: active ? 'var(--brand-050)' : 'transparent',
                  cursor: 'pointer',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                  <span className="mono" style={{ fontSize: 11.5, color: active ? 'var(--brand)' : 'var(--muted)', fontWeight: 600 }}>{item.id}</span>
                  <span className="mono tnum" style={{ fontSize: 11, color: 'var(--faint)' }}>{pct(item.confidence)}</span>
                </div>
                <div style={{ fontSize: 12.5, color: 'var(--ink)', fontWeight: 550, marginTop: 3 }}>
                  {titleize(item.semantic_type)}
                </div>
                <div className="text-faint" style={{ fontSize: 11, marginTop: 2 }}>
                  {titleize(item.source_type)} · {item.extracted_facts.length} fact{item.extracted_facts.length === 1 ? '' : 's'}
                </div>
              </button>
            );
          })}
        </div>

        {/* Detail */}
        <EvidenceDetail item={selected} />
      </div>
    </section>
  );
}
