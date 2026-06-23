import { Layers, ArrowRight } from 'lucide-react';
import TentativeBanner from '../../components/TentativeBanner.jsx';

export default function Stage2({ onContinue, onApprove, onNavigate }) {
  return (
    <div className="h-full flex flex-col overflow-hidden">
      <TentativeBanner stageId={2} onGoToStage={onNavigate} />
      <div className="shrink-0 border-b border-paper-deep bg-paper px-6 py-4">
        <div className="font-mono text-[10px] tracking-widest uppercase text-accent mb-1">
          Stage 02 · Not yet implemented
        </div>
        <h1 className="text-xl font-semibold tracking-tight">
          Table of Contents & Analysis Specifications
        </h1>
        <p className="text-ink-muted text-xs mt-1">
          Synthesizes the TOC and full analysis specs from the rules approved in Stage 01.
          Backend module: <span className="font-mono">backend/toc_synthesis/</span>
        </p>
      </div>
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <Layers size={32} className="text-ink-faint mx-auto mb-3" />
          <div className="text-base font-medium mb-2">Awaiting backend</div>
          <p className="text-ink-muted text-xs leading-relaxed">
            Once <span className="font-mono">backend/app/routers/stage2_toc.py</span> is in
            place, this view will list synthesized outputs with their full analysis specifications.
          </p>
        </div>
      </div>
      <FooterButtons onContinue={onContinue} onApprove={onApprove} />
    </div>
  );
}

function FooterButtons({ onContinue, onApprove }) {
  return (
    <div className="shrink-0 border-t border-paper-deep bg-paper px-6 py-3 flex items-center justify-between">
      <div className="font-mono text-xs text-ink-muted">Stub — passes through.</div>
      <div className="flex gap-2">
        <button
          onClick={onContinue}
          className="text-xs px-4 py-2 rounded border border-ink-faint btn-ghost font-medium flex items-center gap-2"
        >
          Continue without approval <ArrowRight size={12} />
        </button>
        <button
          onClick={onApprove}
          className="btn-primary text-xs px-4 py-2 rounded font-medium flex items-center gap-2"
        >
          Approve & continue <ArrowRight size={12} />
        </button>
      </div>
    </div>
  );
}
