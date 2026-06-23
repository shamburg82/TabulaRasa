import { useState, useEffect } from 'react';
import { Save, X } from 'lucide-react';
import DetailSection from '../../components/DetailSection.jsx';
import Pill from '../../components/Pill.jsx';
import { ConfidenceBar } from '../../components/Confidence.jsx';
import { CitationList } from '../../components/Citation.jsx';
import ReviewActions from '../../components/ReviewActions.jsx';
import { formatOrigin } from '../../lib/format.js';
import { useCurrentUser } from '../../lib/UserContext.jsx';

function SpecRow({ label, value, note }) {
  if (!value) return null;
  return (
    <tr className="border-b border-paper-deep">
      <td className="font-mono text-[10px] uppercase tracking-wider text-ink-muted py-1.5 align-top" style={{ width: 130 }}>
        {label}
      </td>
      <td className="py-1.5 align-top">
        <div className="text-xs">{value}</div>
        {note && <div className="font-mono text-[10px] text-ink-faint mt-0.5">↳ {note}</div>}
      </td>
    </tr>
  );
}

export default function AnalysisDetail({ analysis, rules, onReview }) {
  const { username } = useCurrentUser();
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(() => snapshot(analysis));

  useEffect(() => { setForm(snapshot(analysis)); setEditing(false); }, [analysis.analysis_id]);

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
          title: form.title,
          output_type: form.output_type,
          population: form.population,
          endpoint: form.endpoint || null,
          method: form.method || null,
          comparison: form.comparison || null,
          visit_structure: form.visit_structure || null,
          rationale: form.rationale || null,
        },
      });
      setEditing(false);
    } finally {
      setBusy(false);
    }
  };

  const e = analysis.review?.edited_value || {};
  const view = {
    title: e.title ?? analysis.title,
    output_type: e.output_type ?? analysis.output_type,
    population: e.population ?? analysis.population,
    endpoint: e.endpoint ?? analysis.endpoint,
    method: e.method ?? analysis.method,
    comparison: e.comparison ?? analysis.comparison,
    visit_structure: e.visit_structure ?? analysis.visit_structure,
    rationale: e.rationale ?? analysis.rationale,
  };

  const appliedRules = (analysis.applicable_rules || [])
    .map((rid) => rules.find((r) => r.rule_id === rid))
    .filter(Boolean);

  return (
    <div className="p-5">
      <div className="flex items-center gap-2 mb-2">
        <span className="font-mono text-xs text-ink-muted">{analysis.analysis_id}</span>
        <Pill variant="muted">
          {view.output_type === 'T' ? 'Table' : view.output_type === 'L' ? 'Listing' :
           view.output_type === 'F' ? 'Figure' : 'Output'}
        </Pill>
        <Pill variant={analysis.origin === 'implied' ? 'ai' : 'muted'}>
          {formatOrigin(analysis.origin)}
        </Pill>
        {(analysis.review?.status || 'pending') === 'pending' && (
          <Pill variant="warn">tentative</Pill>
        )}
      </div>

      {editing ? (
        <EditForm form={form} setForm={setForm} onSave={saveEdits}
          onCancel={() => { setForm(snapshot(analysis)); setEditing(false); }} busy={busy} />
      ) : (
        <>
          <div className="text-sm font-medium leading-snug mb-4">{view.title}</div>

          {analysis.confidence != null && (
            <DetailSection label="Confidence">
              <ConfidenceBar value={analysis.confidence} variant="labeled" />
            </DetailSection>
          )}

          <DetailSection label="Specification">
            <table className="w-full">
              <tbody>
                <SpecRow label="Population" value={view.population} />
                <SpecRow label="Endpoint" value={view.endpoint} />
                <SpecRow label="Method" value={view.method} />
                <SpecRow label="Comparison" value={view.comparison} />
                <SpecRow label="Visit structure" value={view.visit_structure} />
                <SpecRow label="Subgroups"
                  value={analysis.subgroups?.length ? analysis.subgroups.join(', ') : 'None'} />
                {analysis.convention_basis && (
                  <SpecRow label="Convention basis" value={analysis.convention_basis} note="implied analysis" />
                )}
              </tbody>
            </table>
          </DetailSection>

          {appliedRules.length > 0 && (
            <DetailSection label={`Applied rules · ${appliedRules.length}`}>
              <div className="flex flex-wrap gap-1">
                {appliedRules.map((r) => (
                  <span key={r.rule_id} title={r.statement}
                    className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-paper-deep border border-paper-deep">
                    {r.rule_id}
                  </span>
                ))}
              </div>
            </DetailSection>
          )}

          <DetailSection label={`Citations · ${analysis.citations?.length || 0}`}>
            <CitationList citations={analysis.citations} />
          </DetailSection>

          {view.rationale && (
            <DetailSection label="AI Rationale">
              <div className="pill-ai rounded p-3 text-xs leading-relaxed">{view.rationale}</div>
            </DetailSection>
          )}

          {analysis.review?.reason && (
            <DetailSection label="Reviewer note">
              <div className="text-xs text-ink-muted italic">{analysis.review.reason}</div>
            </DetailSection>
          )}

          <ReviewActions
            review={analysis.review}
            onUpdate={handleReview}
            onEdit={() => setEditing(true)}
            busy={busy}
          />
        </>
      )}
    </div>
  );
}

function snapshot(analysis) {
  const e = analysis.review?.edited_value || {};
  return {
    title: e.title ?? analysis.title ?? '',
    output_type: e.output_type ?? analysis.output_type ?? 'T',
    population: e.population ?? analysis.population ?? '',
    endpoint: e.endpoint ?? analysis.endpoint ?? '',
    method: e.method ?? analysis.method ?? '',
    comparison: e.comparison ?? analysis.comparison ?? '',
    visit_structure: e.visit_structure ?? analysis.visit_structure ?? '',
    rationale: e.rationale ?? analysis.rationale ?? '',
  };
}

function EditForm({ form, setForm, onSave, onCancel, busy }) {
  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  return (
    <div className="space-y-3">
      <FormField label="Title">
        <input value={form.title} onChange={(e) => update('title', e.target.value)}
          className="w-full bg-white border border-paper-deep rounded px-2 py-1.5 text-sm" />
      </FormField>
      <div className="grid grid-cols-2 gap-3">
        <FormField label="Output type">
          <select value={form.output_type} onChange={(e) => update('output_type', e.target.value)}
            className="w-full bg-white border border-paper-deep rounded px-2 py-1.5 text-sm">
            <option value="T">Table</option>
            <option value="L">Listing</option>
            <option value="F">Figure</option>
          </select>
        </FormField>
        <FormField label="Population">
          <input value={form.population} onChange={(e) => update('population', e.target.value)}
            className="w-full bg-white border border-paper-deep rounded px-2 py-1.5 text-sm font-mono" />
        </FormField>
      </div>
      <FormField label="Endpoint">
        <input value={form.endpoint} onChange={(e) => update('endpoint', e.target.value)}
          className="w-full bg-white border border-paper-deep rounded px-2 py-1.5 text-sm" />
      </FormField>
      <FormField label="Method">
        <textarea value={form.method} onChange={(e) => update('method', e.target.value)} rows={2}
          className="w-full bg-white border border-paper-deep rounded p-2 text-xs" />
      </FormField>
      <div className="grid grid-cols-2 gap-3">
        <FormField label="Comparison">
          <input value={form.comparison} onChange={(e) => update('comparison', e.target.value)}
            className="w-full bg-white border border-paper-deep rounded px-2 py-1.5 text-sm" />
        </FormField>
        <FormField label="Visit structure">
          <input value={form.visit_structure} onChange={(e) => update('visit_structure', e.target.value)}
            className="w-full bg-white border border-paper-deep rounded px-2 py-1.5 text-sm" />
        </FormField>
      </div>
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
