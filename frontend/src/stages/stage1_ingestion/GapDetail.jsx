import { useState, useEffect } from 'react';
import { AlertCircle, Save, X } from 'lucide-react';
import DetailSection from '../../components/DetailSection.jsx';
import Pill from '../../components/Pill.jsx';
import { ConfidenceBar } from '../../components/Confidence.jsx';
import { CitationList } from '../../components/Citation.jsx';
import ReviewActions from '../../components/ReviewActions.jsx';
import { useCurrentUser } from '../../lib/UserContext.jsx';

export default function GapDetail({ gap, onReview }) {
  const { username } = useCurrentUser();
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(() => snapshot(gap));

  useEffect(() => { setForm(snapshot(gap)); setEditing(false); }, [gap.gap_id]);

  const handleReview = async (payload) => {
    setBusy(true);
    try { await onReview(payload); } finally { setBusy(false); }
  };

  const saveEdits = async () => {
    setBusy(true);
    try {
      await onReview({
        status: 'edited',
        reviewer: username,
        reason: null,
        edited_value: {
          description: form.description,
          affected_area: form.affected_area,
          proposed_default: form.proposed_default || null,
          default_source: form.default_source || null,
          rationale: form.rationale || null,
        },
      });
      setEditing(false);
    } finally {
      setBusy(false);
    }
  };

  const e = gap.review?.edited_value || {};
  const view = {
    description: e.description ?? gap.description,
    affected_area: e.affected_area ?? gap.affected_area,
    proposed_default: e.proposed_default ?? gap.proposed_default,
    default_source: e.default_source ?? gap.default_source,
    rationale: e.rationale ?? gap.rationale,
  };

  return (
    <div className="p-5">
      <div className="flex items-center gap-2 mb-2">
        <AlertCircle size={14} className="text-warn" />
        <span className="font-mono text-xs text-ink-muted">{gap.gap_id}</span>
        <Pill variant="warn">gap</Pill>
        {(gap.review?.status || 'pending') === 'pending' && (
          <Pill variant="warn">tentative</Pill>
        )}
      </div>

      {editing ? (
        <EditForm form={form} setForm={setForm} onSave={saveEdits}
          onCancel={() => { setForm(snapshot(gap)); setEditing(false); }} busy={busy} />
      ) : (
        <>
          <div className="text-sm font-medium leading-snug mb-3">{view.description}</div>

          {gap.confidence != null && (
            <DetailSection label="Confidence">
              <ConfidenceBar value={gap.confidence} variant="labeled" />
            </DetailSection>
          )}

          <DetailSection label="Affected area">
            <div className="text-xs">{view.affected_area}</div>
          </DetailSection>

          {view.proposed_default && (
            <DetailSection label="Proposed default">
              <div className="bg-white border border-paper-deep rounded p-3 text-xs leading-relaxed">
                {view.proposed_default}
              </div>
              {view.default_source && (
                <div className="font-mono text-[10px] text-ink-faint mt-1">source: {view.default_source}</div>
              )}
            </DetailSection>
          )}

          {view.rationale && (
            <DetailSection label="AI Rationale">
              <div className="pill-ai rounded p-3 text-xs leading-relaxed">{view.rationale}</div>
            </DetailSection>
          )}

          <DetailSection label={`Citations · ${gap.citations?.length || 0}`}>
            <CitationList citations={gap.citations} />
          </DetailSection>

          {gap.review?.reason && (
            <DetailSection label="Reviewer note">
              <div className="text-xs text-ink-muted italic">{gap.review.reason}</div>
            </DetailSection>
          )}

          <ReviewActions
            review={gap.review}
            onUpdate={handleReview}
            onEdit={() => setEditing(true)}
            busy={busy}
          />
        </>
      )}
    </div>
  );
}

function snapshot(gap) {
  const e = gap.review?.edited_value || {};
  return {
    description: e.description ?? gap.description ?? '',
    affected_area: e.affected_area ?? gap.affected_area ?? '',
    proposed_default: e.proposed_default ?? gap.proposed_default ?? '',
    default_source: e.default_source ?? gap.default_source ?? '',
    rationale: e.rationale ?? gap.rationale ?? '',
  };
}

function EditForm({ form, setForm, onSave, onCancel, busy }) {
  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  return (
    <div className="space-y-3">
      <FormField label="Description">
        <textarea value={form.description} onChange={(e) => update('description', e.target.value)} rows={2}
          className="w-full bg-white border border-paper-deep rounded p-2 text-xs" />
      </FormField>
      <FormField label="Affected area">
        <textarea value={form.affected_area} onChange={(e) => update('affected_area', e.target.value)} rows={2}
          className="w-full bg-white border border-paper-deep rounded p-2 text-xs" />
      </FormField>
      <FormField label="Proposed default">
        <textarea value={form.proposed_default} onChange={(e) => update('proposed_default', e.target.value)} rows={3}
          className="w-full bg-white border border-paper-deep rounded p-2 text-xs" />
      </FormField>
      <FormField label="Default source">
        <input value={form.default_source} onChange={(e) => update('default_source', e.target.value)}
          className="w-full bg-white border border-paper-deep rounded px-2 py-1.5 text-sm font-mono" />
      </FormField>
      <FormField label="Rationale">
        <textarea value={form.rationale} onChange={(e) => update('rationale', e.target.value)} rows={2}
          className="w-full bg-white border border-paper-deep rounded p-2 text-xs" />
      </FormField>
      <div className="flex gap-2 justify-end pt-2 border-t border-paper-deep">
        <button onClick={onCancel} disabled={busy}
          className="text-xs px-3 py-1.5 rounded border border-ink-faint btn-ghost flex items-center gap-1.5">
          <X size={12} /> Cancel
        </button>
        <button onClick={onSave} disabled={busy}
          className="btn-primary text-xs px-3 py-1.5 rounded flex items-center gap-1.5 disabled:opacity-50">
          <Save size={12} /> Save edits
        </button>
      </div>
    </div>
  );
}

function FormField({ label, children }) {
  return (
    <div>
      <div className="font-mono text-[10px] uppercase tracking-wider text-ink-muted mb-1">{label}</div>
      {children}
    </div>
  );
}
