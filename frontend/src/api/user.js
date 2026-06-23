/**
 * GET /me -> { username, source }
 * Uses Posit Connect / proxy headers, falls back to OS user in Workbench.
 */

import { api } from './client.js';

export async function getCurrentUser() {
  try {
    return await api.get('me');
  } catch {
    return { username: 'unknown', source: 'fallback' };
  }
}
