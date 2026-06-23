import { useCallback, useEffect, useState } from 'react';
import { Plus, ArrowRight, X, Loader2 } from 'lucide-react';
import { listStudies } from '../api/studies.js';
import { useStudy } from '../lib/StudyContext.jsx';
import { formatDate, formatExtractionStatus } from '../lib/format.js';
import Pill from '../components/Pill.jsx';
import SapUpload from '../components/SapUpload.jsx';

function statusVariant(status) {
  return (
    {
      approved: 'ok',
      awaiting_review: 'warn',
      running: 'ai',
      failed: 'accent',
    }[status] || 'muted'
  );
}

export default function LandingPage() {
  const { setStudyId, markUploaded } = useStudy();
  const [studies, setStudies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showNew, setShowNew] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setStudies(await listStudies());
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-paper-bg">
      <header className="shrink-0 bg-ink text-paper">
        <div className="px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="font-display text-3xl leading-none">
              Tabula<span style={{ color: '#d97757' }}>·</span>Rasa
            </div>
            <div className="font-mono text-[11px] tracking-[0.2em] uppercase opacity-60">
              Clinical TLF Automation
            </div>
          </div>
          <button
            onClick={() => setShowNew(true)}
            className="text-xs px-3 py-2 rounded bg-white text-ink hover:bg-paper flex items-center gap-2"
          >
            <Plus size={14} /> New study
          </button>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-6 py-10">
          <div className="mb-8">
            <h1 className="font-display text-4xl leading-none mb-2">Studies</h1>
            <p className="text-ink-muted text-sm">
              Open an existing study to continue, or start a new one by uploading its SAP.
            </p>
          </div>

          {loading && (
            <div className="flex items-center justify-center py-12 text-ink-muted text-xs gap-2">
              <Loader2 size={16} className="animate-spin" /> Loading studies...
            </div>
          )}

          {error && (
            <div className="bg-paper border border-paper-deep rounded p-4 text-xs text-accent font-mono">
              {error.message || String(error)}
            </div>
          )}

          {!loading && !error && studies.length === 0 && (
            <div className="bg-paper border border-paper-deep rounded p-10 text-center">
              <div className="text-base font-medium mb-2">No studies yet</div>
              <p className="text-ink-muted text-xs mb-6">
                Start by uploading a Statistical Analysis Plan. The 5-pass extraction will run
                in the background and surface rules, analyses, and gaps for review.
              </p>
              <button
                onClick={() => setShowNew(true)}
                className="btn-primary text-xs px-4 py-2 rounded font-medium inline-flex items-center gap-2"
              >
                <Plus size={12} /> New study
              </button>
            </div>
          )}

          {!loading && studies.length > 0 && (
            <div className="bg-paper border border-paper-deep rounded overflow-hidden">
              <table className="data">
                <thead>
                  <tr>
                    <th style={{ width: 140 }}>Study</th>
                    <th style={{ width: 80 }}>Version</th>
                    <th style={{ width: 130 }}>Status</th>
                    <th>Counts</th>
                    <th style={{ width: 180 }}>Updated</th>
                    <th style={{ width: 90 }}></th>
                  </tr>
                </thead>
                <tbody>
                  {studies.map((s) => (
                    <tr key={s.study_id} onClick={() => setStudyId(s.study_id)}>
                      <td className="font-mono text-sm font-semibold">{s.study_id}</td>
                      <td className="font-mono text-xs">v{s.version}</td>
                      <td>
                        <Pill variant={statusVariant(s.status)}>
                          {formatExtractionStatus(s.status)}
                        </Pill>
                      </td>
                      <td className="text-xs text-ink-muted">
                        {s.rules_count != null && (
                          <span className="font-mono">
                            {s.rules_count} rules · {s.analyses_count} analyses · {s.gaps_count} gaps
                          </span>
                        )}
                      </td>
                      <td className="font-mono text-xs text-ink-muted">
                        {formatDate(s.updated_at)}
                      </td>
                      <td>
                        <span className="text-xs inline-flex items-center gap-1 text-ink">
                          Open <ArrowRight size={11} />
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>

      {showNew && (
        <NewStudyModal
          onClose={() => setShowNew(false)}
          onUploaded={({ studyId }) => {
            setShowNew(false);
            markUploaded(studyId);
            setStudyId(studyId);
          }}
        />
      )}
    </div>
  );
}

function NewStudyModal({ onClose, onUploaded }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-8"
      style={{ background: 'rgba(26,26,26,0.5)', backdropFilter: 'blur(4px)' }}
    >
      <div className="bg-paper border border-paper-deep rounded shadow-xl max-w-xl w-full max-h-[90vh] flex flex-col">
        <div className="shrink-0 px-5 py-3 border-b border-paper-deep flex items-center justify-between">
          <div>
            <div className="font-mono text-[10px] uppercase tracking-wider text-accent">
              New study
            </div>
            <div className="text-base font-semibold">Upload Statistical Analysis Plan</div>
          </div>
          <button onClick={onClose} className="btn-ghost p-1.5 rounded">
            <X size={16} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-5">
          <SapUpload onUploaded={onUploaded} />
        </div>
      </div>
    </div>
  );
}
