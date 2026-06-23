import { Loader2, AlertCircle, FileText } from 'lucide-react';

export function LoadingState({ label = 'Loading...' }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-ink-muted text-xs gap-2">
      <Loader2 size={18} className="animate-spin" />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({ error }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-accent text-xs gap-2 p-6 text-center">
      <AlertCircle size={20} />
      <div className="font-medium">Something went wrong</div>
      <div className="text-ink-muted font-mono text-[11px] max-w-md">
        {error?.message || String(error)}
      </div>
    </div>
  );
}

export function EmptyState({ label = 'Select an item for details.', icon: Icon = FileText }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-ink-muted text-xs gap-2 p-6 text-center">
      <Icon size={20} className="text-ink-faint" />
      <span>{label}</span>
    </div>
  );
}
