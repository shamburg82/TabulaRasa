import { useState } from 'react';
import { CheckCircle2, Edit3, X, Loader2 } from 'lucide-react';
import Pill from './Pill.jsx';
import { formatStatus, formatDate } from '../lib/format.js';
import { useCurrentUser } from '../lib/UserContext.jsx';

/**
 * Review action bar. Wires up Accept / Edit / Reject and reopen.
 *
 * Props:
 *   review     current ReviewState
 *   onUpdate   async (review) => void  parent runs the API call
 *   onEdit     () => void              parent toggles its edit form
 *   busy       boolean
 */
export default function ReviewActions({ review, onUpdate, onEdit, busy }) {
  const { username } = useCurrentUser();
  const [confirming, setConfirming] = useState(null); // null | 'reject'
  const [reason, setReason] = useState('');

  const submit = (status, extra = {}) =>
    onUpdate({
      status,
      reviewer: username,
      reason: extra.reason || null,
      edited_value: extra.edited_value || null,
    });

  if (review?.status && review.status !== 'pending') {
    return (
      <div className="border-t border-paper-deep mt-3 pt-3 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <Pill
            variant={
              review.status === 'accepted' ? 'ok' :
              review.status === 'edited' ? 'warn' : 'accent'
            }
          >
            {formatStatus(review.status)}
          </Pill>
          {review.reviewer && (
            <span className="text-ink-muted">
              by {review.reviewer} · {formatDate(review.reviewed_at)}
            </span>
          )}
        </div>
        <div className="flex gap-2">
          {onEdit && (
            <button
              onClick={onEdit}
              className="btn-ghost text-xs px-2.5 py-1 rounded border border-ink-faint flex items-center gap-1.5"
              disabled={busy}
            >
              <Edit3 size={11} /> Edit
            </button>
          )}
          <button
            className="btn-ghost text-xs px-2.5 py-1 rounded border border-ink-faint"
            onClick={() => submit('pending')}
            disabled={busy}
          >
            Reopen
          </button>
        </div>
      </div>
    );
  }

  if (confirming === 'reject') {
    return (
      <div className="border-t border-paper-deep mt-3 pt-3 space-y-2">
        <div className="font-mono text-[10px] uppercase tracking-wider text-ink-muted">
          Rejection reason (required)
        </div>
        <textarea
          autoFocus
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Why is this incorrect? Feeds correction memory."
          className="w-full bg-white border border-paper-deep rounded p-2 text-xs leading-relaxed h-20"
        />
        <div className="flex gap-2 justify-end">
          <button
            className="text-xs px-3 py-1.5 rounded border border-ink-faint btn-ghost"
            onClick={() => { setConfirming(null); setReason(''); }}
          >
            Cancel
          </button>
          <button
            disabled={!reason.trim() || busy}
            className="btn-primary text-xs px-3 py-1.5 rounded disabled:opacity-50"
            onClick={() => {
              submit('rejected', { reason: reason.trim() });
              setConfirming(null);
              setReason('');
            }}
          >
            Confirm reject
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="border-t border-paper-deep mt-3 pt-3 flex gap-2">
      <button
        disabled={busy}
        onClick={() => submit('accepted')}
        className="btn-primary text-xs px-3 py-1.5 rounded flex items-center gap-1.5 disabled:opacity-50"
      >
        {busy ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={12} />}
        Accept
      </button>
      {onEdit && (
        <button
          disabled={busy}
          onClick={onEdit}
          className="text-xs px-3 py-1.5 rounded border border-ink-faint btn-ghost flex items-center gap-1.5"
        >
          <Edit3 size={12} /> Edit
        </button>
      )}
      <button
        disabled={busy}
        onClick={() => setConfirming('reject')}
        className="text-xs px-3 py-1.5 rounded border border-ink-faint btn-ghost flex items-center gap-1.5"
      >
        <X size={12} /> Reject
      </button>
    </div>
  );
}
