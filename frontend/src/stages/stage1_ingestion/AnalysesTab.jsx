import { useState, useMemo } from 'react';
import DataTable from '../../components/DataTable.jsx';
import Pill from '../../components/Pill.jsx';
import { ConfidenceBar } from '../../components/Confidence.jsx';
import { EmptyState } from '../../components/StatusIndicator.jsx';
import SelectionToolbar, { useSelection } from '../../components/SelectionToolbar.jsx';
import { useCurrentUser } from '../../lib/UserContext.jsx';
import AnalysisDetail from './AnalysisDetail.jsx';

function reviewPill(review) {
  const s = review?.status || 'pending';
  if (s === 'accepted') return <Pill variant="ok">accepted</Pill>;
  if (s === 'edited') return <Pill variant="warn">edited</Pill>;
  if (s === 'rejected') return <Pill variant="accent">rejected</Pill>;
  return <Pill variant="muted">pending</Pill>;
}

export default function AnalysesTab({ analyses, rules, onReview, onReviewBulk }) {
  const { username } = useCurrentUser();
  const [selectedId, setSelectedId] = useState(analyses[0]?.analysis_id ?? null);
  const sel = useSelection();
  const [bulkBusy, setBulkBusy] = useState(false);

  const columns = [
    { key: 'analysis_id', label: 'ID', width: 70, mono: true },
    { key: 'output_type', label: 'T/L/F', width: 50,
      render: (r) => (
        <span className="font-mono text-xs font-semibold" style={{
          color: r.output_type === 'F' ? '#8b1e1e' : r.output_type === 'L' ? '#2d5016' : '#1a1a1a',
        }}>{r.output_type || '—'}</span>
      ) },
    { key: 'title', label: 'Title', render: (r) => r.title },
    { key: 'population', label: 'Population', width: 110,
      render: (r) => <span className="font-mono text-xs text-ink-muted">{r.population || '—'}</span> },
    { key: 'origin', label: 'Origin', width: 80,
      render: (r) => r.origin === 'implied' ? <Pill variant="ai">implied</Pill> : <Pill variant="muted">explicit</Pill> },
    { key: 'confidence', label: 'Conf.', width: 110,
      render: (r) => <ConfidenceBar value={r.confidence} /> },
    { key: 'review', label: 'Status', width: 90, render: (r) => reviewPill(r.review) },
  ];

  const selected = useMemo(() => analyses.find((a) => a.analysis_id === selectedId) || null, [analyses, selectedId]);

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
      <SelectionToolbar count={sel.count} onClear={sel.clear}
        onAccept={acceptSelected} onReject={rejectSelected} busy={bulkBusy} />
      <div className="grid grid-cols-12 overflow-hidden" style={{ height: sel.count > 0 ? 'calc(100% - 41px)' : '100%' }}>
        <div className="col-span-7 border-r border-paper-deep scroll-y">
          <DataTable
            columns={columns} rows={analyses}
            selectedId={selectedId} onSelect={setSelectedId}
            getRowId={(r) => r.analysis_id} empty="No analyses identified."
            selectable selectedIds={sel.ids}
            onToggleOne={sel.toggle}
            onToggleAll={() => sel.toggleAll(analyses, (a) => a.analysis_id)}
          />
        </div>
        <div className="col-span-5 scroll-y bg-paper">
          {selected ? (
            <AnalysisDetail analysis={selected} rules={rules}
              onReview={(p) => onReview(selected.analysis_id, p)} />
          ) : (
            <EmptyState label="Select an analysis to review." />
          )}
        </div>
      </div>
    </>
  );
}
