import { createContext, useContext, useState, useMemo, useCallback } from 'react';

/**
 * Per-stage UX state. Tracks:
 *   - visited:    user has opened this stage
 *   - advanced:   user has moved past this stage (clicked Continue)
 *   - approved:   user has formally signed off on this stage
 *   - advancedAt / approvedAt timestamps for staleness checks
 *
 * Derived:
 *   - isTentative(id):    advanced && !approved, OR any upstream is tentative
 *   - canApprove(id):     prerequisite reviews done (caller checks item-level)
 *   - tentativeChain(id): list of upstream stages that make `id` tentative
 *
 * The tentative concept propagates downstream: if Stage 01 is advanced
 * without approval, every stage after it is tentative even if its own
 * content has been generated.
 */

const StageProgressContext = createContext(null);

const N_STAGES = 5;

function initialState() {
  const obj = {};
  for (let i = 1; i <= N_STAGES; i++) {
    obj[i] = {
      visited: i === 1,
      advanced: false,
      advancedAt: null,
      approved: false,
      approvedAt: null,
    };
  }
  return obj;
}

export function StageProgressProvider({ children }) {
  const [stages, setStages] = useState(initialState);

  const visit = useCallback((id) => {
    setStages((prev) => (prev[id]?.visited ? prev : { ...prev, [id]: { ...prev[id], visited: true } }));
  }, []);

  const advance = useCallback((id) => {
    setStages((prev) => {
      const next = { ...prev };
      next[id] = { ...prev[id], visited: true, advanced: true, advancedAt: Date.now() };
      if (id < N_STAGES) {
        next[id + 1] = { ...prev[id + 1], visited: true };
      }
      return next;
    });
  }, []);

  const approve = useCallback((id) => {
    setStages((prev) => ({
      ...prev,
      [id]: { ...prev[id], approved: true, approvedAt: Date.now() },
    }));
  }, []);

  const reset = useCallback((id) => {
    setStages((prev) => ({
      ...prev,
      [id]: { ...prev[id], approved: false, approvedAt: null },
    }));
  }, []);

  const value = useMemo(() => {
    const isTentative = (id) => {
      for (let i = 1; i <= id; i++) {
        if (stages[i].advanced && !stages[i].approved) return true;
        if (i === id && stages[i].advanced && !stages[i].approved) return true;
      }
      return false;
    };
    const tentativeChain = (id) => {
      const chain = [];
      for (let i = 1; i < id; i++) {
        if (stages[i].advanced && !stages[i].approved) chain.push(i);
      }
      return chain;
    };
    const stageStatus = (id, activeId) => {
      const s = stages[id];
      if (s.approved) return 'approved';
      if (s.advanced) return 'tentative';
      if (id === activeId) return 'in_progress';
      if (s.visited) return 'visited';
      return 'pending';
    };
    return { stages, visit, advance, approve, reset, isTentative, tentativeChain, stageStatus };
  }, [stages, visit, advance, approve, reset]);

  return <StageProgressContext.Provider value={value}>{children}</StageProgressContext.Provider>;
}

export function useStageProgress() {
  const ctx = useContext(StageProgressContext);
  if (!ctx) throw new Error('useStageProgress must be used inside StageProgressProvider');
  return ctx;
}
