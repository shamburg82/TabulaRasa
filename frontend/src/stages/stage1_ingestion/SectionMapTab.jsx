import DataTable from '../../components/DataTable.jsx';
import { formatSectionRole } from '../../lib/format.js';

/**
 * Drives the section map from SapExtraction.section_map directly.
 * (DocumentSection structural data with pages/chars isn't exposed by the
 * backend yet; if you add a /studies/{id}/sections endpoint later, join here.)
 */
export default function SectionMapTab({ map }) {
  const columns = [
    {
      key: 'number',
      label: '§',
      width: 80,
      render: (r) => <span className="font-mono text-xs text-ink-muted">{r.number || '—'}</span>,
    },
    { key: 'title', label: 'Title', render: (r) => r.title },
    {
      key: 'roles',
      label: 'Semantic roles',
      width: 360,
      render: (r) => (
        <div className="flex flex-wrap gap-1">
          {(r.roles || []).map((role) => (
            <span
              key={role}
              className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-paper-deep border border-paper-deep"
            >
              {formatSectionRole(role)}
            </span>
          ))}
        </div>
      ),
    },
  ];

  return (
    <div className="h-full overflow-hidden">
      <div className="h-full scroll-y">
        <DataTable
          columns={columns}
          rows={map}
          getRowId={(r) => r.section_id}
          empty="No sections mapped."
        />
      </div>
    </div>
  );
}
