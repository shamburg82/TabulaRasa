import { CheckCircle2, Circle, AlertTriangle } from 'lucide-react';

export const STAGES = [
  { id: 1, name: 'SAP Ingestion', subtitle: 'Extract rules & analyses' },
  { id: 2, name: 'TOC & Specs', subtitle: 'Synthesize deliverables' },
  { id: 3, name: 'Shell Generation', subtitle: 'Mock layouts & metadata' },
  { id: 4, name: 'ADaM Reconciliation', subtitle: 'Map to data' },
  { id: 5, name: 'Code Generation', subtitle: 'ARD + rendering' },
];

/**
 * Status values per stage:
 *   approved       formally signed off
 *   tentative      advanced without approval
 *   in_progress    currently active
 *   visited        seen but not advanced
 *   pending        not yet reached
 */
export default function StageTabs({ active, status, onChange }) {
  return (
    <div className="px-2 flex items-stretch bg-ink border-t border-white/10">
      {STAGES.map((s) => {
        const st = status[s.id];
        const isActive = active === s.id;
        return (
          <button
            key={s.id}
            onClick={() => onChange(s.id)}
            className={`px-4 py-2.5 text-left relative ${
              isActive ? 'bg-white text-black' : 'text-paper hover:bg-white/5'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <span className="font-mono text-xs opacity-50">0{s.id}</span>
              <span className="text-xs font-medium">{s.name}</span>
              {st === 'approved' && (
                <CheckCircle2 size={12} style={{ color: isActive ? '#2d5016' : '#8fbf6e' }} title="Approved" />
              )}
              {st === 'tentative' && (
                <AlertTriangle size={12} style={{ color: isActive ? '#8a5a00' : '#e8b04a' }} title="Tentative — advanced without approval" />
              )}
              {st === 'in_progress' && (
                <div className="w-1.5 h-1.5 rounded-full pulse-dot" style={{ background: isActive ? '#8b1e1e' : '#e8b04a' }} />
              )}
              {st === 'visited' && <Circle size={10} className="opacity-50" />}
              {st === 'pending' && <Circle size={10} className="opacity-30" />}
            </div>
            {isActive && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent" />}
          </button>
        );
      })}
    </div>
  );
}
