/**
 * Stage 1 (SAP Ingestion) API client.
 *
 *   POST  studies/{study_id}/sap                            (multipart)
 *   GET   studies/{study_id}/extraction[?version=]
 *   GET   studies/{study_id}/audit[?stage=]
 *   POST  studies/{study_id}/extraction/{version}/review
 *   POST  studies/{study_id}/extraction/{version}/approve
 *   POST  studies/{study_id}/extraction/{version}/rules    NEW: user-added rule
 *   POST  reference                                          (multipart)
 *   POST  search
 *   GET   me                                                 NEW: current user
 *
 * All paths are relative; client.js resolves them against document.baseURI
 * and prepends "api/" so they work behind any proxy prefix.
 */

import { api, USE_MOCK } from './client.js';
import * as mock from './mock-stage1.js';

export async function uploadSap(studyId, { file, versionTag, houseStandards }) {
  if (USE_MOCK) return mock.uploadSap(studyId, { file, versionTag, houseStandards });
  const fd = new FormData();
  fd.append('file', file);
  if (versionTag) fd.append('version_tag', versionTag);
  if (houseStandards) fd.append('house_standards', houseStandards);
  return api.postForm(`studies/${studyId}/sap`, fd);
}

export async function getExtraction(studyId, version) {
  if (USE_MOCK) return mock.getExtraction(studyId, version);
  return api.get(`studies/${studyId}/extraction`, version ? { version } : undefined);
}

export async function getAudit(studyId, stage) {
  if (USE_MOCK) return mock.getAudit(studyId, stage);
  return api.get(`studies/${studyId}/audit`, stage ? { stage } : undefined);
}

/**
 * itemKind: "rules" | "analyses" | "gaps"
 * payload:  { status, reviewer, reason?, edited_value? }
 */
export async function postReview(studyId, version, itemKind, itemId, payload) {
  if (USE_MOCK) return mock.postReview(studyId, version, itemKind, itemId, payload);
  return api.post(`studies/${studyId}/extraction/${version}/review`, {
    item_kind: itemKind,
    item_id: itemId,
    ...payload,
  });
}

/**
 * Bulk review: sequential per-item POST. If you add a /review/bulk endpoint
 * on the backend later, just swap the implementation here.
 */
export async function postReviewBulk(studyId, version, itemKind, itemIds, payload) {
  const results = [];
  for (const id of itemIds) {
    try {
      results.push({ id, ok: true, result: await postReview(studyId, version, itemKind, id, payload) });
    } catch (e) {
      results.push({ id, ok: false, error: e });
    }
  }
  return results;
}

export async function postApprove(studyId, version, reviewer) {
  if (USE_MOCK) return mock.postApprove(studyId, version, reviewer);
  return api.post(`studies/${studyId}/extraction/${version}/approve`, { reviewer });
}

export async function postUserRule(studyId, version, body) {
  if (USE_MOCK) return mock.postUserRule(studyId, version, body);
  return api.post(`studies/${studyId}/extraction/${version}/rules`, body);
}

export async function uploadReference({ file, docType, studyId, versionTag }) {
  if (USE_MOCK) return mock.uploadReference({ file, docType, studyId, versionTag });
  const fd = new FormData();
  fd.append('file', file);
  fd.append('doc_type', docType);
  if (studyId) fd.append('study_id', studyId);
  if (versionTag) fd.append('version_tag', versionTag);
  return api.postForm('reference', fd);
}

export async function search({ query, studyId, docTypes, limit = 8 }) {
  if (USE_MOCK) return mock.search({ query, studyId, docTypes, limit });
  return api.post('search', { query, study_id: studyId, doc_types: docTypes, limit });
}
