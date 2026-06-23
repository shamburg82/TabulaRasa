/**
 * Confidence display. Pass a 0-1 value or null/undefined to render nothing.
 * Variants:
 *   inline      compact bar + % (for table cells)
 *   labeled     bar + % + descriptor (for detail panels)
 */

function bandFor(c) {
  if (c >= 0.85) return { label: 'high', color: '#2d5016' };
  if (c >= 0.70) return { label: 'medium', color: '#8a5a00' };
  return { label: 'low', color: '#8b1e1e' };
}

export function ConfidenceBar({ value, variant = 'inline', width = 64 }) {
  if (value == null || Number.isNaN(value)) return null;
  const pct = Math.round(value * 100);
  const band = bandFor(value);

  if (variant === 'inline') {
    return (
      <span className="inline-flex items-center gap-1.5" title={`${band.label} confidence`}>
        <span className="font-mono text-[11px] text-ink-muted">{pct}%</span>
        <span
          className="inline-block rounded-full overflow-hidden"
          style={{ width, height: 4, background: '#e5e0d3' }}
        >
          <span
            className="block h-full"
            style={{ width: `${pct}%`, background: band.color }}
          />
        </span>
      </span>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <span className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: '#e5e0d3' }}>
        <span className="block h-full" style={{ width: `${pct}%`, background: band.color }} />
      </span>
      <span className="font-mono text-xs">{pct}%</span>
      <span className="font-mono text-[10px] text-ink-muted uppercase">{band.label}</span>
    </div>
  );
}
