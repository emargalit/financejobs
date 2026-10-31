const API_URL = (process.env.REACT_APP_API_URL || '').replace(/\/$/, '');

export async function api(path, options = {}) {
  const response = await fetch(`${API_URL}/api/${path}`, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail || Object.entries(data).map(([field, errors]) => `${field}: ${Array.isArray(errors) ? errors.join(' ') : errors}`).join(' ');
    const error = new Error(detail || `Request failed (${response.status}). Please try again.`);
    error.status = response.status;
    throw error;
  }
  return data;
}

export function post(path, data) {
  return api(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
}
