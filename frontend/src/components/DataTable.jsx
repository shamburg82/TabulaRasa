/**
 * Tabular list with sticky header. Optionally renders a leading
 * selection-checkbox column when `selectable`, `selectedIds`, and
 * `onToggleAll`/`onToggleOne` are provided.
 */
export default function DataTable({
  columns,
  rows,
  selectedId,
  onSelect,
  getRowId,
  empty = 'No items',
  // selection (optional)
  selectable = false,
  selectedIds,
  onToggleOne,
  onToggleAll,
}) {
  if (!rows || rows.length === 0) {
    return <div className="p-8 text-center text-ink-muted text-xs">{empty}</div>;
  }

  const allSelected =
    selectable && rows.length > 0 && rows.every((r) => selectedIds?.has(getRowId(r)));
  const someSelected =
    selectable && !allSelected && rows.some((r) => selectedIds?.has(getRowId(r)));

  return (
    <table className="data">
      <thead>
        <tr>
          {selectable && (
            <th style={{ width: 32 }}>
              <input
                type="checkbox"
                aria-label="Select all"
                checked={allSelected}
                ref={(el) => { if (el) el.indeterminate = someSelected; }}
                onChange={() => onToggleAll?.()}
                onClick={(e) => e.stopPropagation()}
              />
            </th>
          )}
          {columns.map((c) => (
            <th key={c.key} style={{ width: c.width, textAlign: c.align || 'left' }}>
              {c.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => {
          const id = getRowId(r);
          const isChecked = selectable && selectedIds?.has(id);
          return (
            <tr
              key={id}
              onClick={() => onSelect && onSelect(id)}
              className={selectedId === id ? 'is-selected' : ''}
            >
              {selectable && (
                <td
                  style={{ width: 32 }}
                  onClick={(e) => { e.stopPropagation(); onToggleOne?.(id); }}
                >
                  <input
                    type="checkbox"
                    checked={!!isChecked}
                    onChange={() => onToggleOne?.(id)}
                    onClick={(e) => e.stopPropagation()}
                    aria-label={`Select ${id}`}
                  />
                </td>
              )}
              {columns.map((c) => (
                <td
                  key={c.key}
                  style={{ textAlign: c.align || 'left' }}
                  className={c.mono ? 'font-mono text-xs' : 'text-xs leading-snug'}
                >
                  {c.render ? c.render(r) : r[c.key]}
                </td>
              ))}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
