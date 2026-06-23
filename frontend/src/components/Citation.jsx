/**
 * Render a Citation (section + page + optional quote).
 * Schema: { section_number, section_title, section_id, page, quote }
 */
export default function Citation({ citation }) {
  if (!citation) return null;
  const refLine = [
    citation.section_number && `§${citation.section_number}`,
    citation.section_title,
    citation.page && `p.${citation.page}`,
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <div className="text-xs">
      {citation.quote && (
        <div className="bg-paper-deep border-l-2 border-ink-faint pl-3 py-2 italic leading-relaxed">
          “{citation.quote}”
        </div>
      )}
      <div className="font-mono text-[10px] text-ink-faint mt-1">{refLine}</div>
    </div>
  );
}

export function CitationList({ citations }) {
  if (!citations || citations.length === 0) {
    return <div className="text-xs text-ink-faint">No citations.</div>;
  }
  return (
    <div className="space-y-2">
      {citations.map((c, i) => (
        <Citation key={i} citation={c} />
      ))}
    </div>
  );
}
