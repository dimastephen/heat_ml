import axios, { type AxiosRequestHeaders } from 'axios';

const api = axios.create({
  baseURL: '/api',
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('heatml.access');
  if (token) {
    const headers = (config.headers ?? {}) as AxiosRequestHeaders;
    headers.Authorization = `Bearer ${token}`;
    config.headers = headers;
  }
  return config;
});

export const AuthAPI = {
  login: (email: string, password: string) =>
    api.post('/auth/login', new URLSearchParams({ username: email, password })),
  register: (email: string, password: string) => api.post('/auth/register', { email, password }),
  me: () => api.get('/auth/me'),
};

export const DatasetAPI = {
  list: (params?: { limit?: number; offset?: number }) => api.get('/files/datasets', { params }),
  create: (name: string) => api.post('/files/datasets', { name }),
  uploadFile: (batchId: string, fileType: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return api.post(`/files/datasets/${batchId}/upload/${fileType}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

export const ForecastAPI = {
  list: (params?: { limit?: number; offset?: number }) => api.get('/forecasts', { params }),
  get: (jobId: string) => api.get(`/forecasts/${jobId}`),
  create: (batchId: string, params?: Record<string, unknown>) =>
    api.post('/forecasts', { batch_id: batchId, params }),
  getSeries: (jobId: string, limit = 1000) => api.get(`/forecasts/${jobId}/series`, { params: { limit } }),
  listHouses: (jobId: string) => api.get(`/forecasts/${jobId}/houses`),
  getHouseSeries: (jobId: string, houseId: string, limit = 1000) =>
    api.get(`/forecasts/${jobId}/houses/${houseId}`, { params: { limit } }),
  downloadReport: (jobId: string) => api.get(`/reports/forecasts/${jobId}/pdf`, { responseType: 'blob' }),
};

export const ReportsAPI = {
  list: () => api.get('/reports'),
  getByBatch: (batchId: string) => api.get(`/reports/datasets/${batchId}`),
};

export default api;
