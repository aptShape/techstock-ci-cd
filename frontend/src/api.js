// Accept an origin or an API base, and append /api exactly once.
export function normalizeApiBase(value = '/api') {
  const base = value.trim().replace(/\/+$/, '').replace(/(?:\/api)+$/, '');
  return `${base}/api`;
}
