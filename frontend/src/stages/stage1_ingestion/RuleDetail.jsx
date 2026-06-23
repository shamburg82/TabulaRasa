import { useState, useEffect } from 'react';
import { Save, X } from 'lucide-react';
import DetailSection from '../../components/DetailSection.jsx';
import Pill from '../../components/Pill.jsx';
import { ConfidenceBar } from '../../components/Confidence.jsx';
import { CitationList } from '../../components/Citation.jsx';
import ReviewActions from '../../components/ReviewActions.jsx';
import { formatScope } from '../../lib/format.js';
import { useCurrentUser } from '../../lib/UserContext.jsx';

const SCOPES = [
  { value: 'global', label: 'Global' },
  { value: 'safety_only', label: 'Safety only' },
  { value: 'efficacy_only', label: 'Efficacy only' },
  { value: 'domain_specific', label: 'Domain specific' },
  { value: 'population_specific', label: 'Population specific' },
];

function isUserAdded(rule) {
  return rule.origin === 'user_added' || (rule.rule_id || '').startsWith('U-');
}

export default function RuleDetail({ rule, onReview }) {
  const { username } = useCurrentUser();
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(() => snapshot(rule));

  // reset edit form when switching rules
  useEffect(() => { setForm(snapshot(rule)); setEditing(false); }, [rule.rule_id]);

  const handleReview = async (payload) => {
    setBusy(true);
    try { await onReview(payload); } finally { setBusy(false); }
  };

  const saveEdits = async () => {
    const edited_value = {
      statement: form.statement,
      scope: form.scope,
      scope_detail: form.scope_detail || null,
      category: form.category,
      rationale: form.rationale || null,
    };
    setBusy(true);
    try {
      await onReview({
        status: 'edited',
        reviewer: username,
        reason: null,
        edited_value,
      });
      setEditing(false);
    } finally {
      setBusy(false);
    }
  };

  // Show the edited values where present so the user sees their last edits
  const e = rule.review?.edited_value || {};
  const view = {
    statement: e.statement ?? rule.statement,
    scope: e.scope ?? rule.scope,
    scope_detail: e.scope_detail ?? rule.scope_detail,
    category: e.category ?? rule.category,
    rationale: e.rationale ?? rule.rationale,
  };

  return (
    <div className="p-5">
      <div className="flex items-center gap-2 mb-2">
        <span className="font-mono text-xs text-ink-muted">{rule.rule_id}</span>
        {isUserAdded(rule) && <Pill variant="ai">user-added</Pill>}
        <Pill variant="muted">{formatScope(view.scope)}</Pill>
        {view.scope_detail && (
          <span className="font-mono text-[10px] text-ink-faint">{view.scope_detail}</span>
        )}
        {(rule.review?.status || 'pending') === 'pending' && (
          <Pill variant="warn">tentative</Pill>
        )}
      </div>

      {editing ? (
        <EditForm
          form={form}
          setForm={setForm}
          onSave={saveEdits}
          onCancel={() => { setForm(snapshot(rule)); setEditing(false); }}
          busy={busy}
        />
      ) : (
        <>
          <div className="text-sm leading-snug mb-4">{view.statement}</div>

          {rule.confidence != null && !isUserAdded(rule) && (
            <DetailSection label="Confidence">
              <ConfidenceBar value={rule.confidence} variant="labeled" />
            </DetailSection>
          )}

          <DetailSection label="Category">
            <div className="font-mono text-xs">{view.category}</div>
          </DetailSection>

          <DetailSection label={`Citations · ${rule.citations?.length || 0}`}>
            <CitationList citations={rule.citations} />
          </DetailSection>

          {view.rationale && (
            <DetailSection label={isUserAdded(rule) ? 'Author rationale' : 'AI Rationale'}>
              <div className="pill-ai rounded p-3 text-xs leading-relaxed">{view.rationale}</div>
            </DetailSection>
          )}

          {rule.review?.reason && rule.review.reason !== 'user-added' && (
            <DetailSection label="Reviewer note">
              <div className="text-xs text-ink-muted italic">{rule.review.reason}</div>
            </DetailSection>
          )}

          <ReviewActions
            review={rule.review}
            onUpdate={handleReview}
            onEdit={() => setEditing(true)}
            busy={busy}
          />
        </>
      )}
    </div>
  );
}

function snapshot(rule) {
  const e = rule.review?.edited_value || {};
  return {
    statement: e.statement ?? rule.statement ?? '',
    scope: e.scope ?? rule.scope ?? 'global',
    scope_detail: e.scope_detail ?? rule.scope_detail ?? '',
    category: e.category ?? rule.category ?? '',
    rationale: e.rationale ?? rule.rationale ?? '',
  };
}

function EditForm({ form, setForm, onSave, onCancel, busy }) {
  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  return (
    <div className="space-y-3">
      <FormField label="Statement">
        <textarea
          value={form.statement}
          onChange={(e) => update('statement', e.target.value)}
          rows={3}
          className="w-full bg-white border border-paper-deep rounded p-2 text-xs leading-relaxed"
        />
      </FormField>
      <div className="grid grid-cols-2 gap-3">
        <FormField label="Scope">
          <select
            value={form.scope}
            onChange={(e) => update('scope', e.target.value)}
            className="w-full bg-white border border-paper-deep rounded px-2 py-1.5 text-sm"
          >
            {SCOPES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </FormField>
        <FormField label="Scope detail">
          <input
            value={form.scope_detail}
            onChange={(e) => update('scope_detail', e.target.value)}
            className="w-full bg-white border border-paper-deep rounded px-2 py-1.5 text-sm"
          />
        </FormField>
      </div>
      <FormField label="Category">
        <input
          value={form.category}
          onChange={(e) => update('category', e.target.value)}
          className="w-full bg-white border border-paper-deep rounded px-2 py-1.5 text-sm font-mono"
        />
      </FormField>
      <FormField label="Rationale">
        <textarea
          value={form.rationale}
          onChange={(e) => update('rationale', e.target.value)}
          rows={2}
          className="w-full bg-white border border-paper-deep rounded p-2 text-xs leading-relaxed"
        />
      </FormField>
      <div className="flex gap-2 justify-end pt-2 border-t border-paper-deep">
        <button
          onClick={onCancel}
          disabled={busy}
          className="text-xs px-3 py-1.5 rounded border border-ink-faint btn-ghost flex items-center gap-1.5"
        >
          <X size={12} /> Cancel
        </button>
        <button
          onClick={onSave}
          disabled={busy}
          className="btn-primary text-xs px-3 py-1.5 rounded flex items-center gap-1.5 disabled:opacity-50"
        >
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
