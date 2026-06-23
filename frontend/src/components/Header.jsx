import { GitBranch, Clock, ArrowLeft } from 'lucide-react';
import { useStudy } from '../lib/StudyContext.jsx';
import { useCurrentUser } from '../lib/UserContext.jsx';

export default function Header() {
  const { studyId, clear } = useStudy();
  const { username, initials } = useCurrentUser();
  return (
    <header className="shrink-0 bg-ink text-paper">
      <div className="px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={clear}
            className="text-xs px-2 py-1 rounded hover:bg-white/10 opacity-80 hover:opacity-100 flex items-center gap-1.5"
            title="Back to studies"
          >
            <ArrowLeft size={14} /> Studies
          </button>
          <div className="font-display text-2xl leading-none pl-4 border-l border-white/20">
            Tabula<span style={{ color: '#d97757' }}>·</span>Rasa
          </div>
          {studyId && (
            <div className="flex items-center gap-2 font-mono text-xs opacity-70 pl-4 border-l border-white/20">
              <span>STUDY</span>
              <span className="text-white">{studyId}</span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-4 font-mono text-xs">
          <button className="px-2.5 py-1.5 rounded opacity-70 hover:opacity-100 hover:bg-white/10 flex items-center gap-2">
            <GitBranch size={12} /> Versions
          </button>
          <button className="px-2.5 py-1.5 rounded opacity-70 hover:opacity-100 hover:bg-white/10 flex items-center gap-2">
            <Clock size={12} /> Audit Log
          </button>
          <div className="flex items-center gap-2 pl-4 border-l border-white/20" title={username}>
            <div className="w-6 h-6 rounded-full bg-white/10 flex items-center justify-center text-[10px]">{initials}</div>
            <span className="opacity-80 max-w-[140px] truncate">{username}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
