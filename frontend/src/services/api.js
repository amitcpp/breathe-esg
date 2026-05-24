const API_URL = import.meta.env.VITE_API_URL || '';

function getToken() {
  return localStorage.getItem('access_token');
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = { ...options.headers };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    // Try to refresh token
    const refreshToken = localStorage.getItem('refresh_token');
    if (refreshToken) {
      const refreshRes = await fetch(`${API_URL}/api/auth/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: refreshToken }),
      });
      if (refreshRes.ok) {
        const data = await refreshRes.json();
        localStorage.setItem('access_token', data.access);
        headers['Authorization'] = `Bearer ${data.access}`;
        const retryRes = await fetch(`${API_URL}${path}`, { ...options, headers });
        if (!retryRes.ok) throw new Error(`API error: ${retryRes.status}`);
        return retryRes.json();
      }
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || errData.error || `API error: ${res.status}`);
  }

  return res.json();
}

export const api = {
  // Auth
  login: (username, password) =>
    request('/api/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  register: (data) =>
    request('/api/auth/register/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  me: () => request('/api/auth/me/'),

  // Dashboard
  dashboardSummary: () => request('/api/dashboard/summary/'),

  // Ingestion
  uploadFile: (file, sourceType) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('source_type', sourceType);
    return request('/api/ingestion/upload/', {
      method: 'POST',
      body: formData,
    });
  },

  ingestionHistory: () => request('/api/ingestion/history/'),
  ingestionDetail: (id) => request(`/api/ingestion/history/${id}/`),

  // Emissions
  getRecords: (params = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== '' && v !== null) query.set(k, v);
    });
    return request(`/api/emissions/records/?${query.toString()}`);
  },

  getRecord: (id) => request(`/api/emissions/records/${id}/`),

  // Review
  approveRecords: (recordIds, notes = '') =>
    request('/api/review/approve/', {
      method: 'POST',
      body: JSON.stringify({ record_ids: recordIds, notes }),
    }),

  rejectRecords: (recordIds, notes = '') =>
    request('/api/review/reject/', {
      method: 'POST',
      body: JSON.stringify({ record_ids: recordIds, notes }),
    }),

  lockRecords: (recordIds) =>
    request('/api/review/lock/', {
      method: 'POST',
      body: JSON.stringify({ record_ids: recordIds }),
    }),

  auditTrail: (recordId) =>
    request(`/api/review/audit-trail/?record_id=${recordId || ''}`),
};
