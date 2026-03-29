import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

// API helper functions
export const authAPI = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  register: (data) => api.post('/auth/register', data),
  me: () => api.get('/auth/me'),
};

export const plansAPI = {
  list: (params) => api.get('/plans', { params }),
  get: (id) => api.get(`/plans/${id}`),
  create: (data) => api.post('/plans', data),
  update: (id, data) => api.put(`/plans/${id}`, data),
};

export const membersAPI = {
  list: (params) => api.get('/members', { params }),
  get: (id) => api.get(`/members/${id}`),
  create: (data) => api.post('/members', data),
};

export const claimsAPI = {
  list: (params) => api.get('/claims', { params }),
  get: (id) => api.get(`/claims/${id}`),
  create: (data) => api.post('/claims', data),
  adjudicate: (id, action) => api.post(`/claims/${id}/adjudicate`, action),
};

export const duplicatesAPI = {
  list: (params) => api.get('/duplicates', { params }),
  resolve: (id, resolution) => api.post(`/duplicates/${id}/resolve?resolution=${resolution}`),
};

export const dashboardAPI = {
  metrics: () => api.get('/dashboard/metrics'),
  claimsByStatus: () => api.get('/dashboard/claims-by-status'),
  claimsByType: () => api.get('/dashboard/claims-by-type'),
  recentActivity: (limit = 10) => api.get('/dashboard/recent-activity', { params: { limit } }),
};

export const ediAPI = {
  upload834: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/edi/upload-834', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  upload837: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/edi/upload-837', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  generate835: (dateFrom, dateTo) => 
    api.get('/edi/generate-835', { params: { date_from: dateFrom, date_to: dateTo } }),
};

export const auditAPI = {
  list: (params) => api.get('/audit-logs', { params }),
};
