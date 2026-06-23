import { useMemo, useState, useEffect } from 'react';
import { ArrowRight, RotateCcw, Loader2, CheckCircle2, Upload } from 'lucide-react';

import { useStudy } from '../../lib/StudyContext.jsx';
import { useCurrentUser } from '../../lib/UserContext.jsx';
import { useExtraction, reviewTally } from './hooks.js';
import { LoadingState, ErrorState } from '../../components/StatusIndicator.jsx';
import { formatExtractionStatus } from '../../lib/format.js';
import SapUpload from '../../components/SapUpload.jsx';

import RulesTab from './RulesTab.jsx';
import AnalysesTab from './AnalysesTab.jsx';
import GapsTab from './GapsTab.jsx';
import SectionMapTab from './SectionMapTab.jsx';
import AuditTab from './AuditTab.jsx';

const TABS = [
  { id: 'rules', label: 'Rules' },
  { id: 'analyses', label: 'Analyses' },
  { id: 'gaps', label: 'Gaps' },
  { id: 'section_map', label: 'Section map' },
  { id: 'audit', label: 'Audit' },
];

const PASS_LABELS = {
  section_map: 'Section map',
  explicit_analyses: 'Explicit analyses',
  rules: 'Rules',
  implied_analyses: 'Implied analyses',
  gaps: 'Gaps',
};
const PASS_ORDER = ['section_map', 'explicit_analyses', 'rules', 'implied_analyses', 'gaps'];

export default function Stage1({ onApprove, onContinue }) {
  const { studyId, uploadedAt, markUploaded, clearUploaded } = useStudy();
  const { username } = useCurrentUser();
  const justUploadedAt = uploadedAt[studyId] || 0;

  const {
    data, audit, loading, error, notFound,
    updateReview, updateReviewBulk, approve, addUserRule, reload, uploadPending,
  } = useExtraction(studyId, { justUploadedAt });

  const [tab, setTab] = useState('rules');
  const [showReupload, setShowReupload] = useState(false);

  // once the extraction has refreshed past the upload timestamp, drop the flag
  useEffect(() => {
    if (justUploadedAt && data?.updated_at && Date.parse(data.updated_at) > justUploadedAt) {
      clearUploaded(studyId);
    }
  }, [justUploadedAt, data?.updated_at, studyId, clearUploaded]);

  if (loading && !data && !notFound) return <LoadingState label="Loading extraction..." />;
  if (error && !data && !notFound) return <ErrorState error={error} />;

  if (notFound) {
    return uploadPending
      ? <RunningProgress extraction={null} />
      : <UploadPrompt studyId={studyId} onUploaded={() => markUploaded(studyId)} />;
  }

  if ((data && data.status === 'running') || uploadPending) {
    return <RunningProgress extraction={data} />;
  }

  if (!data) return <LoadingState label="Loading extraction..." />;

  return (
    <>
      <ReviewView
        data={data} audit={audit} tab={tab} setTab={setTab}
        updateReview={updateReview}
        updateReviewBulk={updateReviewBulk}
        addUserRule={addUserRule}
        approve={() => approve(username).then(onApprove)}
        continueWithoutApproval={onContinue}
        reload={reload}
        onReupload={() => setShowReupload(true)}
      />
      {showReupload && (
        <ReuploadModal
          studyId={studyId}
          onClose={() => setShowReupload(false)}
          onUploaded={() => { markUploaded(studyId); setShowReupload(false); }}
        />
      )}
    </>
  );
}

// ---------------------------------------------------------------- //

function UploadPrompt({ studyId, onUploaded }) {
  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-2xl mx-auto px-6 py-10">
        <div className="font-mono text-[10px] tracking-widest uppercase text-accent mb-1">
          Stage 01 · No extraction yet
        </div>
        <h1 className="text-xl font-semibold tracking-tight mb-2">
          Upload the Statistical Analysis Plan
        </h1>
        <p className="text-ink-muted text-xs mb-6 leading-relaxed">
          The 5-pass extraction will run in the background. Study is locked to{' '}
          <span className="font-mono">{studyId}</span>.
        </p>
        <div className="bg-paper border border-paper-deep rounded p-5">
          <SapUpload studyId={studyId} compact onUploaded={onUploaded} />
        </div>
      </div>
    </div>
  );
}

function RunningProgress({ extraction }) {
  const progress = extraction?.pass_progress || {};
  const completed = PASS_ORDER.filter((p) => progress[p] === 'done').length;
  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-2xl mx-auto px-6 py-10">
        <div className="font-mono text-[10px] tracking-widest uppercase text-accent mb-1">
          Stage 01 · {extraction ? 'Running' : 'Starting'}
        </div>
        <h1 className="text-xl font-semibold tracking-tight mb-2 flex items-center gap-2">
          <Loader2 size={18} className="animate-spin" />
          {extraction ? 'Extraction in progress' : 'Extraction starting'}
        </h1>
        <p className="text-ink-muted text-xs mb-6 leading-relaxed">
          {extraction
            ? `${completed} of ${PASS_ORDER.length} passes complete. This page polls every 2 seconds.`
            : 'Waiting for the backend to register the new extraction. This page polls every 2 seconds.'}
        </p>
        <div className="bg-paper border border-paper-deep rounded">
          <table className="data">
            <thead>
              <tr>
                <th style={{ width: 40 }}>#</th>
                <th>Pass</th>
                <th style={{ width: 120 }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {PASS_ORDER.map((p, i) => {
                const status = progress[p] || 'pending';
                return (
                  <tr key={p}>
                    <td className="font-mono text-xs text-ink-muted">{i + 1}</td>
                    <td>{PASS_LABELS[p]}</td>
                    <td>
                      {status === 'done' ? (
                        <span className="text-xs text-ok inline-flex items-center gap-1">
                          <CheckCircle2 size={11} /> done
                        </span>
                      ) : status === 'failed' ? (
                        <span className="text-xs text-accent">failed</span>
                      ) : status === 'in_progress' ? (
                        <span className="text-xs text-warn inline-flex items-center gap-1">
                          <Loader2 size={11} className="animate-spin" /> running
                        </span>
                      ) : (
                        <span className="text-xs text-ink-faint">pending</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {extraction?.error && (
          <div className="mt-4 text-xs text-accent font-mono bg-paper border border-paper-deep p-3 rounded">
            {extraction.error}
          </div>
        )}
      </div>
    </div>
  );
}

function ReviewView({
  data, audit, tab, setTab,
  updateReview, updateReviewBulk, addUserRule, approve, continueWithoutApproval, reload, onReupload,
}) {
  const tally = useMemo(() => {
    const r = reviewTally(data.rules);
    const a = reviewTally(data.analyses);
    const g = reviewTally(data.gaps);
    return {
      total: data.rules.length + data.analyses.length + data.gaps.length,
      reviewed: r.accepted + r.edited + a.accepted + a.edited + g.accepted + g.edited,
      pending: r.pending + a.pending + g.pending,
      rejected: r.rejected + a.rejected + g.rejected,
    };
  }, [data]);

  const tabCounts = {
    rules: data.rules.length,
    analyses: data.analyses.length,
    gaps: data.gaps.length,
    section_map: (data.section_map || []).length,
    audit: audit.length,
  };

  const isApproved = data.status === 'approved';

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="shrink-0 border-b border-paper-deep bg-paper">
        <div className="px-6 py-4 flex items-end justify-between">
          <div>
            <div className="font-mono text-[10px] tracking-widest uppercase text-accent mb-1">
              Stage 01 · {formatExtractionStatus(data.status)}
            </div>
            <h1 className="text-xl font-semibold tracking-tight">Extracted rules & analyses</h1>
            <p className="text-ink-muted text-xs mt-1">
              Rules drive analyses. Corrections here propagate downstream.
            </p>
          </div>
          <div className="flex items-end gap-6 text-xs font-mono">
            <div className="space-y-1 text-right">
              <div><span className="text-ink-muted">Source:</span> doc {data.sap_document_id}</div>
              <div><span className="text-ink-muted">Version:</span> v{data.version}</div>
              <div>
                <span className="text-ink-muted">Reviewed:</span> {tally.reviewed}/{tally.total}
                {tally.pending > 0 && <> · <span className="text-warn">{tally.pending} pending</span></>}
                {tally.rejected > 0 && <> · <span className="text-accent">{tally.rejected} rejected</span></>}
              </div>
            </div>
            <button
              onClick={onReupload}
              className="text-xs px-2.5 py-1.5 rounded border border-ink-faint btn-ghost flex items-center gap-1.5"
              title="Re-upload SAP (creates a new extraction version)"
            >
              <Upload size={12} /> Re-upload SAP
            </button>
          </div>
        </div>
        <div className="px-6 flex gap-1 border-b border-paper-deep">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-2 text-xs font-medium border-b-2 ${
                tab === t.id ? 'border-ink text-ink' : 'border-transparent text-ink-muted hover:text-ink'
              }`}
            >
              {t.label} <span className="font-mono text-ink-faint">· {tabCounts[t.id]}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-hidden">
        {tab === 'rules' && (
          <RulesTab
            rules={data.rules}
            onReview={(id, p) => updateReview('rules', id, p)}
            onReviewBulk={(ids, p) => updateReviewBulk('rules', ids, p)}
            onAddRule={addUserRule}
          />
        )}
        {tab === 'analyses' && (
          <AnalysesTab
            analyses={data.analyses} rules={data.rules}
            onReview={(id, p) => updateReview('analyses', id, p)}
            onReviewBulk={(ids, p) => updateReviewBulk('analyses', ids, p)}
          />
        )}
        {tab === 'gaps' && (
          <GapsTab
            gaps={data.gaps}
            onReview={(id, p) => updateReview('gaps', id, p)}
            onReviewBulk={(ids, p) => updateReviewBulk('gaps', ids, p)}
          />
        )}
        {tab === 'section_map' && <SectionMapTab map={data.section_map || []} />}
        {tab === 'audit' && <AuditTab audit={audit} />}
      </div>

      <div className="shrink-0 border-t border-paper-deep bg-paper px-6 py-3 flex items-center justify-between">
        <div className="font-mono text-xs text-ink-muted">
          {tally.reviewed} of {tally.total} items reviewed
          {tally.pending > 0 && !isApproved && (
            <span className="text-warn"> · {tally.pending} will remain tentative</span>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={reload}
            className="text-xs px-3 py-2 rounded border border-ink-faint btn-ghost flex items-center gap-1.5"
          >
            <RotateCcw size={12} /> Reload
          </button>
          {!isApproved && (
            <button
              onClick={continueWithoutApproval}
              className="text-xs px-4 py-2 rounded border border-ink-faint btn-ghost font-medium flex items-center gap-2"
              title="Move to the next stage without approving. Downstream items will be marked tentative."
            >
              Continue without approval <ArrowRight size={12} />
            </button>
          )}
          <button
            onClick={approve}
            disabled={isApproved || tally.pending > 0}
            className="btn-primary text-xs px-4 py-2 rounded font-medium flex items-center gap-2 disabled:opacity-50"
            title={
              isApproved ? 'Already approved' :
              tally.pending > 0 ? 'Resolve all pending items to approve' :
              'Approve and continue'
            }
          >
            {isApproved ? 'Approved' : 'Approve & continue'} <ArrowRight size={12} />
          </button>
        </div>
      </div>
    </div>
  );
}

function ReuploadModal({ studyId, onClose, onUploaded }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-8"
      style={{ background: 'rgba(26,26,26,0.5)', backdropFilter: 'blur(4px)' }}>
      <div className="bg-paper border border-paper-deep rounded shadow-xl max-w-xl w-full max-h-[90vh] flex flex-col">
        <div className="shrink-0 px-5 py-3 border-b border-paper-deep flex items-center justify-between">
          <div>
            <div className="font-mono text-[10px] uppercase tracking-wider text-accent">Re-upload SAP</div>
            <div className="text-base font-semibold">Study {studyId}</div>
          </div>
          <button onClick={onClose} className="btn-ghost p-1.5 rounded text-ink hover:bg-paper-deep">
            ×
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-5">
          <p className="text-xs text-ink-muted mb-4 leading-relaxed">
            Uploading a new SAP creates a new extraction version. The current review state is preserved on the previous version.
          </p>
          <SapUpload studyId={studyId} compact onUploaded={onUploaded} />
        </div>
      </div>
    </div>
  );
}
