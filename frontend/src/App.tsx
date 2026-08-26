/**
 * DisputeShield shell.
 *
 * Owns the case list and selection; delegates everything about a single case to
 * {@link CaseWorkspace} (mounted with `key`, so switching cases is a clean
 * remount). The left command rail is the only place with global actions — create
 * a case, load the demo set — and the case navigation. All data is real: the
 * list comes from the API, creation posts the exact contract shape, and errors
 * from creation propagate back to the modal so the user sees them.
 */

import { useCallback, useEffect, useState } from 'react';
import { Download, Plus, ShieldCheck } from 'lucide-react';
import type { CaseCreateRequest, DisputeCase } from './lib/types';
import { createCase, listCases, loadDemo } from './lib/api';
import { ApiError } from './lib/api';
import CaseList from './components/CaseList';
import CaseWorkspace from './components/CaseWorkspace';
import NewCaseModal from './components/NewCaseModal';
import { ErrorState, Loading } from './components/ui';

export default function App() {
  const [cases, setCases] = useState<DisputeCase[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);

  const refresh = useCallback(async (): Promise<DisputeCase[]> => {
    const data = await listCases();
    setCases(data);
    return data;
  }, []);

  useEffect(() => {
    // Runs once on mount; initial state is already loading=true / error=null,
    // so no synchronous setState is needed before the fetch.
    let cancelled = false;
    listCases()
      .then((data) => {
        if (cancelled) return;
        setCases(data);
        setSelectedId((cur) => cur ?? (data[0]?.id ?? null));
      })
      .catch((e) => {
        if (!cancelled) setListError(e instanceof ApiError ? e.message : 'Could not load cases.');
      })
      .finally(() => {
        if (!cancelled) setListLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Re-throws on failure so the modal can render the error and stay open.
  const handleCreateCase = async (req: CaseCreateRequest) => {
    const created = await createCase(req);
    await refresh();
    setSelectedId(created.id);
    setModalOpen(false);
  };

  const handleLoadDemo = async () => {
    setDemoLoading(true);
    setListError(null);
    try {
      const res = await loadDemo();
      const data = await refresh();
      const firstCreated = res.created_cases[0];
      setSelectedId(firstCreated ?? data[0]?.id ?? null);
    } catch (e) {
      setListError(e instanceof ApiError ? e.message : 'Could not load the demo cases.');
    } finally {
      setDemoLoading(false);
    }
  };

  return (
    <div className="app-shell">
      {/* Command rail */}
      <aside className="rail">
        <div className="rail__brand">
          <span className="rail__mark">
            <ShieldCheck size={19} />
          </span>
          <div>
            <div className="rail__title">DisputeShield</div>
            <div className="rail__subtitle">Evidence Intelligence</div>
          </div>
        </div>

        <div className="rail__actions">
          <button className="btn-rail" onClick={() => setModalOpen(true)}>
            <Plus size={16} /> New case
          </button>
          <button className="btn-rail btn-rail--ghost" onClick={handleLoadDemo} disabled={demoLoading}>
            {demoLoading ? <span className="spinner spinner--rail" /> : <Download size={15} />}
            Load demo set
          </button>
        </div>

        <div className="rail__list">
          <div className="rail-label">Cases{cases.length > 0 ? ` · ${cases.length}` : ''}</div>
          {listLoading ? (
            <div style={{ color: 'var(--rail-muted)', display: 'flex', alignItems: 'center', gap: 10, padding: '16px 6px' }}>
              <span className="spinner spinner--rail" /> Loading cases…
            </div>
          ) : listError ? (
            <div style={{ padding: '8px 6px' }}>
              <div style={{ color: '#f87171', fontSize: 12.5, lineHeight: 1.5 }}>{listError}</div>
            </div>
          ) : (
            <CaseList cases={cases} selectedId={selectedId} onSelect={setSelectedId} />
          )}
        </div>

        <div className="rail__footer">
          <span style={{ fontSize: 11, color: 'var(--rail-faint)', lineHeight: 1.4 }}>
            Defense-only · never auto-submits · every claim traced to evidence
          </span>
        </div>
      </aside>

      {/* Main region */}
      <main className="main">
        {selectedId ? (
          <CaseWorkspace key={selectedId} caseId={selectedId} />
        ) : listLoading ? (
          <div style={{ display: 'grid', placeItems: 'center', height: '100%' }}>
            <Loading label="Loading…" />
          </div>
        ) : listError ? (
          <div style={{ display: 'grid', placeItems: 'center', height: '100%' }}>
            <ErrorState message={listError} />
          </div>
        ) : (
          <div style={{ display: 'grid', placeItems: 'center', height: '100%', padding: 32 }}>
            <div className="empty">
              <ShieldCheck className="empty__icon" size={40} />
              <div className="text-ink" style={{ fontWeight: 650, fontSize: 16 }}>No case selected</div>
              <div className="text-muted" style={{ maxWidth: 420 }}>
                Create a dispute case or load the five canonical demo cases to see the evidence
                analysis, requirement coverage and compiled package.
              </div>
              <button className="btn btn--primary" onClick={handleLoadDemo} disabled={demoLoading} style={{ marginTop: 8 }}>
                {demoLoading ? <span className="spinner spinner--rail" /> : <Download size={15} />}
                Load demo set
              </button>
            </div>
          </div>
        )}
      </main>

      <NewCaseModal isOpen={modalOpen} onClose={() => setModalOpen(false)} onCreate={handleCreateCase} />
    </div>
  );
}
