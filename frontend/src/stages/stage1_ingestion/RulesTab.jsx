import { useState, useMemo } from 'react';
import { Plus } from 'lucide-react';
import DataTable from '../../components/DataTable.jsx';
import Pill from '../../components/Pill.jsx';
import { ConfidenceBar } from '../../components/Confidence.jsx';
import { EmptyState } from '../../components/StatusIndicator.jsx';
import SelectionToolbar, { useSelection } from '../../components/SelectionToolbar.jsx';
import { useCurrentUser } from '../../lib/UserContext.jsx';
import RuleDetail from './RuleDetail.jsx';
import AddRuleModal from './AddRuleModal.jsx';
import { formatScope } from '../../lib/format.js';

function reviewPill(review) {
  const s = review?.status || 'pending';
  if (s === 'accepted') return <Pill variant="ok">accepted</Pill>;
  if (s === 'edited') return <Pill variant="warn">edited</Pill>;
  if (s === 'rejected') return <Pill variant="accent">rejected</Pill>;
  return <Pill variant="muted">pending</Pill>;
}

function isUserAdded(rule) {
  return rule.origin === 'user_added' || (rule.rule_id || '').startsWith('U-');
}

export default function RulesTab({ rules, onReview, onReviewBulk, onAddRule }) {
  const { username } = useCurrentUser();
  const [selectedId, setSelectedId] = useState(rules[0]?.rule_id ?? null);
  const sel = useSelection();
  const [bulkBusy, setBulkBusy] = useState(false);
  const [showAdd, setShowAdd] = useState(false);

  const columns = [
    { key: 'rule_id', label: 'ID', width: 70, mono: true,
      render: (r) => (
        <span className="flex items-center gap-1">
          <span className="font-mono">{r.rule_id}</span>
          {isUserAdded(r) && <Pill variant="ai">user</Pill>}
        </span>
      ) },
    { key: 'scope', label: 'Scope', width: 110,
      render: (r) => <Pill variant="muted">{formatScope(r.scope)}</Pill> },
    { key: 'category', label: 'Category', width: 140,
      render: (r) => <span className="font-mono text-[11px]">{r.category}</span> },
    { key: 'statement', label: 'Statement', render: (r) => r.statement },
    { key: 'confidence', label: 'Conf.', width: 110,
      render: (r) => isUserAdded(r) ? <span className="text-ink-faint text-[10px]">—</span> : <ConfidenceBar value={r.confidence} /> },
    { key: 'review', label: 'Status', width: 90,
      render: (r) => reviewPill(r.review) },
  ];

  const selected = useMemo(
    () => rules.find((r) => r.rule_id === selectedId) || null,
    [rules, selectedId]
  );

  const acceptSelected = async () => {
    setBulkBusy(true);
    await onReviewBulk([...sel.ids], { status: 'accepted', reviewer: username, reason: null, edited_value: null });
    sel.clear();
    setBulkBusy(false);
  };

  const rejectSelected = async (reason) => {
    setBulkBusy(true);
    await onReviewBulk([...sel.ids], { status: 'rejected', reviewer: username, reason, edited_value: null });
    sel.clear();
    setBulkBusy(false);
  };

  return (
    <>
      <SelectionToolbar
        count={sel.count} onClear={sel.clear}
        onAccept={acceptSelected} onReject={rejectSelected} busy={bulkBusy}
      />
      {sel.count === 0 && (
        <div className="border-b border-paper-deep bg-paper px-4 py-2 flex items-center justify-end">
          <button
            onClick={() => setShowAdd(true)}
            className="text-xs px-2.5 py-1.5 rounded border border-ink-faint btn-ghost flex items-center gap-1.5"
          >
            <Plus size={12} /> Add rule
          </button>
        </div>
      )}
      <div className="grid grid-cols-12 overflow-hidden" style={{ height: 'calc(100% - 41px)' }}>
        <div className="col-span-7 border-r border-paper-deep scroll-y">
          <DataTable
            columns={columns} rows={rules}
            selectedId={selectedId} onSelect={setSelectedId}
            getRowId={(r) => r.rule_id} empty="No rules extracted."
            selectable selectedIds={sel.ids}
            onToggleOne={sel.toggle}
            onToggleAll={() => sel.toggleAll(rules, (r) => r.rule_id)}
          />
        </div>
        <div className="col-span-5 scroll-y bg-paper">
          {selected ? (
            <RuleDetail rule={selected} onReview={(p) => onReview(selected.rule_id, p)} />
          ) : (
            <EmptyState label="Select a rule to review." />
          )}
        </div>
      </div>
      {showAdd && <AddRuleModal onClose={() => setShowAdd(false)} onSubmit={onAddRule} />}
    </>
  );
}
