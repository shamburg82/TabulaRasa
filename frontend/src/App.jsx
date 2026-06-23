import { StudyProvider, useStudy } from './lib/StudyContext.jsx';
import { UserProvider } from './lib/UserContext.jsx';
import { StageProgressProvider } from './lib/StageProgressContext.jsx';
import LandingPage from './pages/LandingPage.jsx';
import StudyWorkspace from './pages/StudyWorkspace.jsx';

function Router() {
  const { studyId } = useStudy();
  return studyId ? <StudyWorkspace /> : <LandingPage />;
}

export default function App() {
  return (
    <UserProvider>
      <StudyProvider>
        <StageProgressProvider>
          <Router />
        </StageProgressProvider>
      </StudyProvider>
    </UserProvider>
  );
}
