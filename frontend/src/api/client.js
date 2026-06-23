/**
 * Base HTTP client.
 *
 * Critical: all API URLs are resolved RELATIVE to document.baseURI so they
 * survive arbitrary proxy prefixes. If the HTML is served at
 *   https://workbench.example.com/p/abc123/
 * then a request for "studies" goes to
 *   https://workbench.example.com/p/abc123/api/studies
 *
 * Never put a leading slash on the path argument. We strip it defensively
 * anyway because new URL("/studies", base) would reset to the origin root.
 */

const apiBase = new URL('api/', document.baseURI);

export class ApiError extends Error {
  constructor(message, { status, body } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

function buildUrl(path, params) {
  const cleanPath = String(path || '').replace(/^\/+/, '');
  const url = new URL(cleanPath, apiBase);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null) url.searchParams.set(k, v);
    }
  }
  return url;
}

async function request(method, path, { params, body, formData } = {}) {
  const url = buildUrl(path, params);
  const init = { method, headers: { Accept: 'application/json' } };
  if (formData) {
    init.body = formData;
  } else if (body !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }

  const res = await fetch(url, init);
  let payload = null;
  const text = await res.text();
  if (text) {
    try { payload = JSON.parse(text); } catch { payload = text; }
  }
  if (!res.ok) {
    const detail = (payload && (payload.detail || payload.message)) || res.statusText;
    throw new ApiError(`${method} ${path} -> ${res.status}: ${detail}`, { status: res.status, body: payload });
  }
  return payload;
}

export const api = {
  get: (path, params) => request('GET', path, { params }),
  post: (path, body) => request('POST', path, { body }),
  postForm: (path, formData) => request('POST', path, { formData }),
  patch: (path, body) => request('PATCH', path, { body }),
  delete: (path) => request('DELETE', path),
};

export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';
