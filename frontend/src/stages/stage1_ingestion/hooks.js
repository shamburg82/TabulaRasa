import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from '../../api/client.js';
import * as stage1 from '../../api/stage1.js';

const POLL_INTERVAL_MS = 2000;
const UPLOAD_STALENESS_MS = 60_000;

/**
 * Drives the Stage 1 view for a given study_id.
 *
 *  - Loads the latest extraction; 404 -> notFound (upload prompt).
 *  - Polls every 2s while status === 'running'.
 *  - justUploadedAt + last seen updated_at gate the "extraction starting"
 *    display so re-uploads don't briefly show the previous version's rules.
 *  - updateReview() optimistically patches one item.
 *  - updateReviewBulk() does the same for many items, with an optional
 *    onProgress callback.
 *  - approve() locks the extraction.
 *  - addUserRule() appends a manually-authored rule.
 */
export function useExtraction(studyId, { justUploadedAt } = {}) {
  const [data, setData] = useState(null);
  const [audit, setAudit] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const pollRef = useRef(null);

  const reload = useCallback(() => setReloadKey((k) => k + 1), []);

  // initial + reload fetch
  useEffect(() => {
    if (!studyId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setNotFound(false);

    Promise.all([
      stage1.getExtraction(studyId).catch((e) => {
        if (e instanceof ApiError && e.status === 404) return null;
        throw e;
      }),
      stage1.getAudit(studyId).catch(() => []),
    ])
      .then(([ext, aud]) => {
        if (cancelled) return;
        if (ext) setData(ext);
        else setNotFound(true);
        setAudit(aud || []);
      })
      .catch((e) => !cancelled && setError(e))
      .finally(() => !cancelled && setLoading(false));

    return () => { cancelled = true; };
  }, [studyId, reloadKey]);

  // poll while running OR while just-uploaded and not yet reflected
  const extractionUpdatedAt = data?.updated_at ? Date.parse(data.updated_at) : 0;
  const uploadIsStale = justUploadedAt && extractionUpdatedAt > justUploadedAt;
  const shouldPoll =
    data?.status === 'running' ||
    notFound ||
    (justUploadedAt && !uploadIsStale);

  useEffect(() => {
    if (!shouldPoll) {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
      return;
    }
    pollRef.current = setInterval(async () => {
      try {
        const ext = await stage1.getExtraction(studyId).catch((e) => {
          if (e instanceof ApiError && e.status === 404) return null;
          throw e;
        });
        if (ext) { setData(ext); setNotFound(false); }
        const aud = await stage1.getAudit(studyId).catch(() => []);
        setAudit(aud || []);
      } catch (e) {
        setError(e);
      }
    }, POLL_INTERVAL_MS);
    return () => {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    };
  }, [studyId, shouldPoll]);

  // --- mutations ---

  const idField = (kind) =>
    kind === 'rules' ? 'rule_id' : kind === 'analyses' ? 'analysis_id' : 'gap_id';

  const updateReview = useCallback(
    async (itemKind, itemId, reviewPayload) => {
      if (!data) return;
      const id = idField(itemKind);
      // optimistic
      setData((prev) => ({
        ...prev,
        [itemKind]: prev[itemKind].map((item) =>
          item[id] === itemId ? { ...item, review: { ...item.review, ...reviewPayload } } : item
        ),
      }));
      try {
        await stage1.postReview(studyId, data.version, itemKind, itemId, reviewPayload);
        const fresh = await stage1.getExtraction(studyId);
        setData(fresh);
      } catch (e) {
        setError(e);
        reload();
      }
    },
    [data, studyId, reload]
  );

  const updateReviewBulk = useCallback(
    async (itemKind, itemIds, reviewPayload) => {
      if (!data || itemIds.length === 0) return;
      const id = idField(itemKind);
      const ids = new Set(itemIds);
      // optimistic
      setData((prev) => ({
        ...prev,
        [itemKind]: prev[itemKind].map((item) =>
          ids.has(item[id]) ? { ...item, review: { ...item.review, ...reviewPayload } } : item
        ),
      }));
      try {
        await stage1.postReviewBulk(studyId, data.version, itemKind, itemIds, reviewPayload);
        const fresh = await stage1.getExtraction(studyId);
        setData(fresh);
      } catch (e) {
        setError(e);
        reload();
      }
    },
    [data, studyId, reload]
  );

  const approve = useCallback(
    async (reviewer) => {
      if (!data) return;
      try {
        const updated = await stage1.postApprove(studyId, data.version, reviewer);
        setData(updated);
      } catch (e) {
        setError(e);
      }
    },
    [data, studyId]
  );

  const addUserRule = useCallback(
    async (body) => {
      if (!data) return;
      try {
        await stage1.postUserRule(studyId, data.version, body);
        const fresh = await stage1.getExtraction(studyId);
        setData(fresh);
        return { ok: true };
      } catch (e) {
        return { ok: false, error: e };
      }
    },
    [data, studyId]
  );

  return {
    data,
    audit,
    loading,
    error,
    notFound,
    reload,
    updateReview,
    updateReviewBulk,
    approve,
    addUserRule,
    /** true when the user just uploaded but the polled extraction
     *  hasn't refreshed yet. Use to gate showing the running state. */
    uploadPending: justUploadedAt && !uploadIsStale,
  };
}

export function reviewTally(items = []) {
  const t = { pending: 0, accepted: 0, edited: 0, rejected: 0 };
  for (const item of items) {
    const s = item?.review?.status || 'pending';
    t[s] = (t[s] || 0) + 1;
  }
  return t;
}
