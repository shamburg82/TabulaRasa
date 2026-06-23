import { createContext, useContext, useState, useMemo, useCallback } from 'react';

/**
 * StudyContext holds the active study selection. Also tracks an upload
 * timestamp per study so Stage 1 can show "Extraction starting" immediately
 * after a SAP re-upload rather than the stale review view.
 */

const StudyContext = createContext(null);

export function StudyProvider({ children }) {
  const [studyId, setStudyId] = useState(null);
  const [uploadedAt, setUploadedAt] = useState({});  // { [studyId]: epochMs }

  const markUploaded = useCallback((sid) => {
    setUploadedAt((prev) => ({ ...prev, [sid]: Date.now() }));
  }, []);

  const clearUploaded = useCallback((sid) => {
    setUploadedAt((prev) => {
      const { [sid]: _, ...rest } = prev;
      return rest;
    });
  }, []);

  const value = useMemo(
    () => ({
      studyId,
      setStudyId,
      clear: () => setStudyId(null),
      uploadedAt,
      markUploaded,
      clearUploaded,
    }),
    [studyId, uploadedAt, markUploaded, clearUploaded]
  );

  return <StudyContext.Provider value={value}>{children}</StudyContext.Provider>;
}

export function useStudy() {
  const ctx = useContext(StudyContext);
  if (!ctx) throw new Error('useStudy must be used inside StudyProvider');
  return ctx;
}
