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
  list: (params) => {
    const apiParams = {};
    if (params?.status) apiParams.plan_status = params.status;
    if (params?.plan_type) apiParams.plan_type = params.plan_type;
    return api.get('/plans', { params: apiParams });
  },
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
  list: (params) => {
    const apiParams = {};
    if (params?.status) apiParams.claim_status = params.status;
    if (params?.claim_type) apiParams.claim_type = params.claim_type;
    if (params?.member_id) apiParams.member_id = params.member_id;
    if (params?.limit) apiParams.limit = params.limit;
    return api.get('/claims', { params: apiParams });
  },
  get: (id) => api.get(`/claims/${id}`),
  create: (data) => api.post('/claims', data),
  adjudicate: (id, action) => api.post(`/claims/${id}/adjudicate`, action),
  batch: (data) => api.post('/claims/batch', data),
  cob: (id, data) => api.post(`/claims/${id}/cob`, data),
};

export const duplicatesAPI = {
  list: (params) => {
    const apiParams = {};
    if (params?.status) apiParams.alert_status = params.status;
    if (params?.duplicate_type) apiParams.duplicate_type = params.duplicate_type;
    return api.get('/duplicates', { params: apiParams });
  },
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
  generate835: (dateFrom, dateTo, format = 'x12') => 
    api.get('/edi/generate-835', { params: { date_from: dateFrom, date_to: dateTo, format } }),
};

export const auditAPI = {
  list: (params) => api.get('/audit-logs', { params }),
};

export const networkAPI = {
  contracts: (params) => api.get('/network/contracts', { params }),
  createContract: (data) => api.post('/network/contracts', data),
  reprice: (claimId) => api.get(`/network/reprice/${claimId}`),
  summary: () => api.get('/network/summary'),
};

export const priorAuthAPI = {
  list: (params) => api.get('/prior-auth', { params }),
  get: (id) => api.get(`/prior-auth/${id}`),
  create: (data) => api.post('/prior-auth', data),
  decide: (id, data) => api.post(`/prior-auth/${id}/decide`, data),
};

export const codeAPI = {
  searchCPT: (q, limit = 50) => api.get('/cpt-codes/search', { params: { q, limit } }),
  searchDental: (q, limit = 50) => api.get('/dental-codes/search', { params: { q, limit } }),
  searchVision: (q, limit = 50) => api.get('/vision-codes/search', { params: { q, limit } }),
  searchHearing: (q, limit = 50) => api.get('/hearing-codes/search', { params: { q, limit } }),
  dbStats: () => api.get('/code-database/stats'),
};

export const batchAPI = {
  processClaims: (data) => api.post('/claims/batch', data),
};
