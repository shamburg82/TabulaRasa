import { useState } from 'react';
import { X, Plus, Loader2 } from 'lucide-react';
import { useCurrentUser } from '../../lib/UserContext.jsx';

const SCOPES = [
  { value: 'global', label: 'Global' },
  { value: 'safety_only', label: 'Safety only' },
  { value: 'efficacy_only', label: 'Efficacy only' },
  { value: 'domain_specific', label: 'Domain specific' },
  { value: 'population_specific', label: 'Population specific' },
];

export default function AddRuleModal({ onClose, onSubmit }) {
  const { username } = useCurrentUser();
  const [statement, setStatement] = useState('');
  const [scope, setScope] = useState('global');
  const [scopeDetail, setScopeDetail] = useState('');
  const [category, setCategory] = useState('');
  const [rationale, setRationale] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const submit = async () => {
    setError(null);
    if (!statement.trim() || !category.trim()) {
      setError('Statement and category are required.');
      return;
    }
    setBusy(true);
    const result = await onSubmit({
      statement: statement.trim(),
      scope,
      scope_detail: scopeDetail.trim() || null,
      category: category.trim(),
      rationale: rationale.trim() || null,
      reviewer: username,
    });
    setBusy(false);
    if (result?.ok) {
      onClose();
    } else {
      setError(result?.error?.message || 'Failed to add rule');
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-8"
      style={{ background: 'rgba(26,26,26,0.5)', backdropFilter: 'blur(4px)' }}
    >
      <div className="bg-paper border border-paper-deep rounded shadow-xl max-w-xl w-full max-h-[90vh] flex flex-col">
        <div className="shrink-0 px-5 py-3 border-b border-paper-deep flex items-center justify-between">
          <div>
            <div className="font-mono text-[10px] uppercase tracking-wider text-accent">
              Add rule
            </div>
            <div className="text-base font-semibold">User-defined rule</div>
          </div>
          <button onClick={onClose} className="btn-ghost p-1.5 rounded">
            <X size={16} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-3">
          <Field label="Statement" required>
            <textarea
              autoFocus
              value={statement}
              onChange={(e) => setStatement(e.target.value)}
              rows={3}
              placeholder="Describe the rule clearly. Example: 'Apply LOCF imputation for PRO endpoints after first dose discontinuation.'"
              className="w-full bg-white border border-paper-deep rounded p-2 text-xs leading-relaxed"
            />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Scope" required>
              <select
                value={scope}
                onChange={(e) => setScope(e.target.value)}
                className="w-full bg-white border border-paper-deep rounded px-2 py-1.5 text-sm"
              >
                {SCOPES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </Field>
            <Field label="Scope detail" hint="optional">
              <input
                value={scopeDetail}
                onChange={(e) => setScopeDetail(e.target.value)}
                placeholder="e.g. AESI tables only"
                className="w-full bg-white border border-paper-deep rounded px-2 py-1.5 text-sm"
              />
            </Field>
          </div>

          <Field label="Category" required hint="treatment_assignment, population, imputation, ...">
            <input
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="e.g. imputation"
              className="w-full bg-white border border-paper-deep rounded px-2 py-1.5 text-sm font-mono"
            />
          </Field>

          <Field label="Rationale" hint="optional">
            <textarea
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
              rows={2}
              placeholder="Why this rule applies, references, scope of effect."
              className="w-full bg-white border border-paper-deep rounded p-2 text-xs leading-relaxed"
            />
          </Field>

          {error && (
            <div className="text-xs text-accent font-mono bg-paper-deep border border-paper-deep p-2 rounded">
              {error}
            </div>
          )}
        </div>

        <div className="shrink-0 px-5 py-3 border-t border-paper-deep flex items-center justify-between">
          <div className="font-mono text-[10px] text-ink-muted">
            Author: {username} — rule will be pre-accepted on save.
          </div>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              disabled={busy}
              className="text-xs px-3 py-1.5 rounded border border-ink-faint btn-ghost"
            >
              Cancel
            </button>
            <button
              onClick={submit}
              disabled={busy}
              className="btn-primary text-xs px-3 py-1.5 rounded flex items-center gap-1.5 disabled:opacity-50"
            >
              {busy ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
              Add rule
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({ label, required, hint, children }) {
  return (
    <div>
      <div className="font-mono text-[10px] uppercase tracking-wider text-ink-muted mb-1 flex items-center gap-2">
        <span>{label}</span>
        {required && <span className="text-accent">*</span>}
        {hint && <span className="normal-case tracking-normal text-ink-faint">— {hint}</span>}
      </div>
      {children}
    </div>
  );
}
