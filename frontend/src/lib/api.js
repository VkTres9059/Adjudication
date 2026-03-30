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
  reconciliation: () => api.get('/members/eligibility/reconciliation'),
  uploadTpaFeed: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/members/eligibility/upload-tpa-feed', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  retroTerms: () => api.get('/members/eligibility/retro-terms'),
  requestRefund: (memberId) => api.post(`/members/${memberId}/request-refund`),
  ageOutAlerts: () => api.get('/members/eligibility/age-out-alerts'),
  auditTrail: (memberId) => api.get(`/members/${memberId}/audit-trail`),
  processPendingEligibility: () => api.post('/claims/process-pending-eligibility'),
  accumulators: (memberId) => api.get(`/members/${memberId}/accumulators`),
  claimsHistory: (memberId) => api.get(`/members/${memberId}/claims-history`),
  dependents: (memberId) => api.get(`/members/${memberId}/dependents`),
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
  fundingHealth: () => api.get('/dashboard/funding-health'),
};

export const reportsAPI = {
  fixedCostVsClaims: () => api.get('/reports/fixed-cost-vs-claims'),
  hourBankDeficiency: () => api.get('/reports/hour-bank-deficiency'),
  predictiveEligibility: () => api.get('/reports/predictive-eligibility'),
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
  validate834: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/edi/validate-834', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  validate837: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/edi/validate-837', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  generate835: (dateFrom, dateTo, format = 'x12') => 
    api.get('/edi/generate-835', { params: { date_from: dateFrom, date_to: dateTo, format } }),
  transactions: (limit = 50, txType) =>
    api.get('/edi/transactions', { params: { limit, ...(txType ? { tx_type: txType } : {}) } }),
  transmissions: (limit = 50) =>
    api.get('/edi/transmissions', { params: { limit } }),
  export834: (vendorId, format = 'hipaa_5010') =>
    api.post('/edi/export-834', null, { params: { vendor_id: vendorId || undefined, format } }),
  exportAuthFeed: (vendorId, format = 'hipaa_5010', dateFrom, dateTo) =>
    api.post('/edi/export-auth-feed', null, { params: {
      vendor_id: vendorId || undefined, format,
      ...(dateFrom ? { date_from: dateFrom } : {}),
      ...(dateTo ? { date_to: dateTo } : {}),
    }}),
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

export const settingsAPI = {
  getGateway: () => api.get('/settings/adjudication-gateway'),
  updateGateway: (data) => api.put('/settings/adjudication-gateway', data),
  getBridge: () => api.get('/settings/bridge-payment'),
  updateBridge: (data) => api.put('/settings/bridge-payment', data),
  getVendors: () => api.get('/settings/vendors'),
  createVendor: (data) => api.post('/settings/vendors', data),
  updateVendor: (id, data) => api.put(`/settings/vendors/${id}`, data),
  deleteVendor: (id) => api.delete(`/settings/vendors/${id}`),
};

export const examinerAPI = {
  holdClaim: (claimId, data) => api.put(`/claims/${claimId}/hold`, data),
  releaseHold: (claimId, notes) => api.put(`/claims/${claimId}/release-hold`, null, { params: { notes } }),
  forcePreventive: (claimId, notes) => api.post(`/claims/${claimId}/force-preventive`, null, { params: { notes } }),
  adjustDeductible: (claimId, amount, notes) => api.post(`/claims/${claimId}/adjust-deductible`, null, { params: { amount, notes } }),
  carrierNotification: (claimId, notes) => api.post(`/claims/${claimId}/carrier-notification`, null, { params: { notes } }),
  getQueue: () => api.get('/examiner/queue'),
  getAllQueues: () => api.get('/examiner/queue/all'),
  quickAction: (claimId, action, notes) => api.post(`/examiner/queue/${claimId}/quick-action`, null, { params: { action, notes } }),
  reassign: (claimId, examinerId) => api.post(`/claims/${claimId}/reassign`, null, { params: { examiner_id: examinerId } }),
  performance: () => api.get('/examiner/performance'),
  listExaminers: () => api.get('/examiner/list'),
};

export const sftpAPI = {
  getConnections: () => api.get('/sftp/connections'),
  createConnection: (data) => api.post('/sftp/connections', data),
  updateConnection: (id, data) => api.put(`/sftp/connections/${id}`, data),
  deleteConnection: (id) => api.delete(`/sftp/connections/${id}`),
  testConnection: (id) => api.post(`/sftp/connections/${id}/test`),
  testInline: (data) => api.post('/sftp/connections/test-inline', data),
  getSchedules: () => api.get('/sftp/schedules'),
  createSchedule: (data) => api.post('/sftp/schedules', data),
  updateSchedule: (id, data) => api.put(`/sftp/schedules/${id}`, data),
  deleteSchedule: (id) => api.delete(`/sftp/schedules/${id}`),
  toggleSchedule: (id) => api.put(`/sftp/schedules/${id}/toggle`),
  runNow: (id) => api.post(`/sftp/schedules/${id}/run-now`),
  intakeLogs: (limit = 50, status) =>
    api.get('/sftp/intake-logs', { params: { limit, ...(status ? { status } : {}) } }),
};

export const hourBankAPI = {
  getLedger: (memberId) => api.get(`/hour-bank/${memberId}`),
  uploadWorkReport: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/hour-bank/upload-work-report', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  runMonthly: (period) => api.post('/hour-bank/run-monthly', null, { params: period ? { period } : {} }),
  manualEntry: (memberId, hours, description) =>
    api.post(`/hour-bank/${memberId}/manual-entry`, null, { params: { hours, description } }),
  bridgePayment: (memberId) => api.post(`/hour-bank/${memberId}/bridge-payment`),
  notifications: (unreadOnly = true) => api.get('/hour-bank/notifications/list', { params: { unread_only: unreadOnly } }),
  markRead: (notifId) => api.put(`/hour-bank/notifications/${notifId}/read`),
};

export const checkRunAPI = {
  getAsoGroups: () => api.get('/check-runs/groups'),
  getPending: (groupId) => api.get('/check-runs/pending', { params: groupId ? { group_id: groupId } : {} }),
  generateFundingRequest: (groupId) => api.post('/check-runs/generate-funding-request', null, { params: { group_id: groupId } }),
  confirmFunding: (runId) => api.post(`/check-runs/${runId}/confirm-funding`),
  execute: (runId) => api.post(`/check-runs/${runId}/execute`),
  list: (groupId, status) => api.get('/check-runs', { params: { ...(groupId ? { group_id: groupId } : {}), ...(status ? { status } : {}) } }),
  get: (runId) => api.get(`/check-runs/${runId}`),
};

export const groupsAPI = {
  getReserveFund: (groupId) => api.get(`/groups/${groupId}/reserve-fund`),
  manualDeposit: (groupId, amount, description) =>
    api.post(`/groups/${groupId}/reserve-deposit`, null, { params: { amount, description } }),
};
