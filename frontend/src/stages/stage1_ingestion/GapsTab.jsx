import { useState, useMemo } from 'react';
import DataTable from '../../components/DataTable.jsx';
import Pill from '../../components/Pill.jsx';
import { ConfidenceBar } from '../../components/Confidence.jsx';
import { EmptyState } from '../../components/StatusIndicator.jsx';
import SelectionToolbar, { useSelection } from '../../components/SelectionToolbar.jsx';
import { useCurrentUser } from '../../lib/UserContext.jsx';
import GapDetail from './GapDetail.jsx';

function reviewPill(review) {
  const s = review?.status || 'pending';
  if (s === 'accepted') return <Pill variant="ok">accepted</Pill>;
  if (s === 'edited') return <Pill variant="warn">edited</Pill>;
  if (s === 'rejected') return <Pill variant="accent">rejected</Pill>;
  return <Pill variant="muted">pending</Pill>;
}

export default function GapsTab({ gaps, onReview, onReviewBulk }) {
  const { username } = useCurrentUser();
  const [selectedId, setSelectedId] = useState(gaps[0]?.gap_id ?? null);
  const sel = useSelection();
  const [bulkBusy, setBulkBusy] = useState(false);

  const columns = [
    { key: 'gap_id', label: 'ID', width: 70, mono: true },
    { key: 'description', label: 'Description', render: (g) => g.description },
    { key: 'affected_area', label: 'Affects', width: 200,
      render: (g) => <span className="text-xs text-ink-muted">{g.affected_area}</span> },
    { key: 'default_source', label: 'Default source', width: 130,
      render: (g) => <span className="font-mono text-[11px] text-ink-muted">{g.default_source || '—'}</span> },
    { key: 'confidence', label: 'Conf.', width: 110,
      render: (g) => <ConfidenceBar value={g.confidence} /> },
    { key: 'review', label: 'Status', width: 90, render: (g) => reviewPill(g.review) },
  ];

  const selected = useMemo(() => gaps.find((g) => g.gap_id === selectedId) || null, [gaps, selectedId]);

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
            columns={columns} rows={gaps}
            selectedId={selectedId} onSelect={setSelectedId}
            getRowId={(g) => g.gap_id} empty="No gaps identified."
            selectable selectedIds={sel.ids}
            onToggleOne={sel.toggle}
            onToggleAll={() => sel.toggleAll(gaps, (g) => g.gap_id)}
          />
        </div>
        <div className="col-span-5 scroll-y bg-paper">
          {selected ? (
            <GapDetail gap={selected} onReview={(p) => onReview(selected.gap_id, p)} />
          ) : (
            <EmptyState label="Select a gap to review." />
          )}
        </div>
      </div>
    </>
  );
}
