/**
 * Pill / badge with semantic variants.
 * variants: muted | ok | warn | accent | ai
 */
export default function Pill({ variant = 'muted', children, className = '' }) {
  const cls =
    {
      muted: 'pill-muted',
      ok: 'pill-ok',
      warn: 'pill-warn',
      accent: 'pill-accent',
      ai: 'pill-ai',
    }[variant] || 'pill-muted';
  return <span className={`${cls} ${className}`}>{children}</span>;
}
