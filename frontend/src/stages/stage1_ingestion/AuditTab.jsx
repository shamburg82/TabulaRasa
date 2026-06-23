import DataTable from '../../components/DataTable.jsx';
import { formatDate } from '../../lib/format.js';

export default function AuditTab({ audit }) {
  const columns = [
    {
      key: 'created_at',
      label: 'Time',
      width: 160,
      render: (r) => <span className="font-mono text-xs text-ink-muted">{formatDate(r.created_at)}</span>,
    },
    {
      key: 'action',
      label: 'Action',
      width: 200,
      render: (r) => <span className="font-mono text-xs">{r.action}</span>,
    },
    {
      key: 'model_id',
      label: 'Model',
      width: 160,
      render: (r) => <span className="font-mono text-xs">{r.model_id}</span>,
    },
    {
      key: 'temperature',
      label: 'T',
      width: 50,
      align: 'right',
      render: (r) => <span className="font-mono text-xs">{r.temperature?.toFixed(1)}</span>,
    },
    {
      key: 'tokens',
      label: 'Tokens (in / out)',
      width: 140,
      align: 'right',
      render: (r) => (
        <span className="font-mono text-xs text-ink-muted">
          {r.input_tokens?.toLocaleString() || '—'} / {r.output_tokens?.toLocaleString() || '—'}
        </span>
      ),
    },
    {
      key: 'latency_ms',
      label: 'Latency',
      width: 90,
      align: 'right',
      render: (r) => (
        <span className="font-mono text-xs text-ink-muted">
          {r.latency_ms ? `${(r.latency_ms / 1000).toFixed(1)}s` : '—'}
        </span>
      ),
    },
    {
      key: 'prompt_sha256',
      label: 'Prompt SHA',
      width: 100,
      render: (r) => (
        <span className="font-mono text-[10px] text-ink-faint">{r.prompt_sha256}</span>
      ),
    },
  ];

  return (
    <div className="h-full overflow-hidden">
      <div className="h-full scroll-y">
        <DataTable
          columns={columns}
          rows={audit}
          getRowId={(r) => `${r.created_at}-${r.action}`}
          empty="No audit records yet."
        />
      </div>
    </div>
  );
}
