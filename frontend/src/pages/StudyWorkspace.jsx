import { useEffect, useState } from 'react';
import Header from '../components/Header.jsx';
import StageTabs from '../components/StageTabs.jsx';
import { useStageProgress } from '../lib/StageProgressContext.jsx';

import Stage1 from '../stages/stage1_ingestion/Stage1.jsx';
import Stage2 from '../stages/stage2_toc/Stage2.jsx';
import Stage3 from '../stages/stage3_shells/Stage3.jsx';
import Stage4 from '../stages/stage4_adam/Stage4.jsx';
import Stage5 from '../stages/stage5_codegen/Stage5.jsx';

export default function StudyWorkspace() {
  const [activeStage, setActiveStage] = useState(1);
  const { stageStatus, visit, advance, approve } = useStageProgress();

  useEffect(() => { visit(activeStage); }, [activeStage, visit]);

  const statusMap = {};
  for (let i = 1; i <= 5; i++) statusMap[i] = stageStatus(i, activeStage);

  const navigateTo = (id) => setActiveStage(id);

  // Advance without approval
  const continueFrom = (id) => {
    advance(id);
    if (id < 5) setActiveStage(id + 1);
  };

  // Approve (caller may or may not advance after)
  const approveStage = (id, { thenAdvance = true } = {}) => {
    approve(id);
    advance(id);
    if (thenAdvance && id < 5) setActiveStage(id + 1);
  };

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Header />
      <StageTabs active={activeStage} status={statusMap} onChange={setActiveStage} />
      <main className="flex-1 overflow-hidden">
        {activeStage === 1 && (
          <Stage1
            onContinue={() => continueFrom(1)}
            onApprove={() => approveStage(1)}
            onNavigate={navigateTo}
          />
        )}
        {activeStage === 2 && (
          <Stage2
            onContinue={() => continueFrom(2)}
            onApprove={() => approveStage(2)}
            onNavigate={navigateTo}
          />
        )}
        {activeStage === 3 && (
          <Stage3
            onContinue={() => continueFrom(3)}
            onApprove={() => approveStage(3)}
            onNavigate={navigateTo}
          />
        )}
        {activeStage === 4 && (
          <Stage4
            onContinue={() => continueFrom(4)}
            onApprove={() => approveStage(4)}
            onNavigate={navigateTo}
          />
        )}
        {activeStage === 5 && (
          <Stage5
            onApprove={() => approveStage(5, { thenAdvance: false })}
            onNavigate={navigateTo}
          />
        )}
      </main>
    </div>
  );
}
