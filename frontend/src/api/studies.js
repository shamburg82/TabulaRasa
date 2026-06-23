/**
 * Studies API. Drives the landing page.
 *
 * Backend endpoint:
 *   GET /studies  ->  [{ study_id, version, status, updated_at, ... }]
 */

import { api, USE_MOCK } from './client.js';
import * as mock from './mock-stage1.js';

export async function listStudies() {
  if (USE_MOCK) return mock.listStudies();
  return api.get('/studies');
}
