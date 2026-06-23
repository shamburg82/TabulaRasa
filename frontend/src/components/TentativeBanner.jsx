import { AlertTriangle, ArrowLeft } from 'lucide-react';
import { useStageProgress } from '../lib/StageProgressContext.jsx';

const STAGE_NAMES = {
  1: 'SAP Ingestion',
  2: 'TOC & Specs',
  3: 'Shell Generation',
  4: 'ADaM Reconciliation',
  5: 'Code Generation',
};

/**
 * Banner shown at the top of a stage when one or more upstream stages
 * have been advanced past without official approval. The banner lists
 * the upstream stages and lets the user jump back to review them.
 */
export default function TentativeBanner({ stageId, onGoToStage }) {
  const { tentativeChain } = useStageProgress();
  const chain = tentativeChain(stageId);
  if (chain.length === 0) return null;

  return (
    <div
      className="shrink-0 px-6 py-2 border-b border-paper-deep flex items-center gap-3"
      style={{ background: '#f5e8c8' }}
    >
      <AlertTriangle size={14} className="text-warn shrink-0" />
      <div className="text-xs leading-relaxed flex-1">
        <span className="font-medium">Tentative output.</span>{' '}
        <span className="text-ink-muted">
          {chain.length === 1 ? 'Upstream stage' : 'Upstream stages'}{' '}
          {chain.map((id, i) => (
            <span key={id}>
              {i > 0 && (i === chain.length - 1 ? ' and ' : ', ')}
              <button
                onClick={() => onGoToStage?.(id)}
                className="font-mono text-ink underline hover:text-accent"
              >
                {String(id).padStart(2, '0')} {STAGE_NAMES[id]}
              </button>
            </span>
          ))}{' '}
          {chain.length === 1 ? 'has' : 'have'} not been approved. Items here may change once review completes.
        </span>
      </div>
      {onGoToStage && (
        <button
          onClick={() => onGoToStage(chain[0])}
          className="text-xs px-2.5 py-1 rounded border border-ink-faint bg-white hover:bg-paper flex items-center gap-1.5 shrink-0"
        >
          <ArrowLeft size={11} /> Review stage {String(chain[0]).padStart(2, '0')}
        </button>
      )}
    </div>
  );
}
