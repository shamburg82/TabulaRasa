export default function DetailSection({ label, children, className = '' }) {
  return (
    <div className={`mb-3 ${className}`}>
      <div className="font-mono text-[10px] uppercase tracking-wider text-ink-muted mb-1.5">
        {label}
      </div>
      {children}
    </div>
  );
}
