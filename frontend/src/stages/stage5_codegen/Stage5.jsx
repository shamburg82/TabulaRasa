import { Code2, CheckCircle2 } from 'lucide-react';
import TentativeBanner from '../../components/TentativeBanner.jsx';

export default function Stage5({ onApprove, onNavigate }) {
  return (
    <div className="h-full flex flex-col overflow-hidden">
      <TentativeBanner stageId={5} onGoToStage={onNavigate} />
      <div className="shrink-0 border-b border-paper-deep bg-paper px-6 py-4">
        <div className="font-mono text-[10px] tracking-widest uppercase text-accent mb-1">
          Stage 05 · Not yet implemented
        </div>
        <h1 className="text-xl font-semibold tracking-tight">Code Generation</h1>
        <p className="text-ink-muted text-xs mt-1">
          ARD builder + per-output renderer; R and SAS.
          Backend module: <span className="font-mono">backend/code_generation/</span>
        </p>
      </div>
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <Code2 size={32} className="text-ink-faint mx-auto mb-3" />
          <div className="text-base font-medium mb-2">Awaiting backend</div>
        </div>
      </div>
      <div className="shrink-0 border-t border-paper-deep bg-paper px-6 py-3 flex items-center justify-between">
        <div className="font-mono text-xs text-ink-muted">Final stage — approve to mark complete.</div>
        <button onClick={onApprove}
          className="btn-primary text-xs px-4 py-2 rounded font-medium flex items-center gap-2">
          Approve <CheckCircle2 size={12} />
        </button>
      </div>
    </div>
  );
}
