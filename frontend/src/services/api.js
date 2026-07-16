import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Documents API Methods
export const uploadDocument = (file, onUploadProgress) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/upload/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress,
  });
};

export const uploadDocumentsBatch = (files, onUploadProgress) => {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  return api.post('/upload/batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
  });
};

export const getDocuments = (page = 1, pageSize = 10, filters = {}) => {
  return api.get('/documents/', { params: { page, page_size: pageSize, ...filters } });
};

export const getDocumentById = (id) => {
  return api.get(`/documents/${id}`);
};

export const deleteDocument = (id) => {
  return api.delete(`/documents/${id}`);
};

// Parser API Methods
export const processDocument = (id) => {
  return api.post(`/parser/process/${id}`);
};

export const bulkProcessDocuments = (documentIds) =>
  api.post('/parser/bulk', { document_ids: documentIds });

export const reprocessDocument = (id) => {
  return api.post(`/parser/reprocess/${id}`);
};

export const getParserResult = (id) => {
  return api.get(`/parser/result/${id}`);
};

// Review API Methods
export const getReview = (id) => {
  return api.get(`/review/${id}`);
};

export const updateFields = (id, fields) => {
  return api.put(`/review/${id}/fields`, fields);
};

export const approveDocument = (id, remarks) => {
  return api.post(`/review/${id}/approve`, { remarks });
};

export const rejectDocument = (id, remarks) => {
  return api.post(`/review/${id}/reject`, { remarks });
};

// Reports API Methods
export const getReports = (page = 1, pageSize = 10) =>
  api.get(`/reports/?page=${page}&page_size=${pageSize}`);

export const getReport = (id) => api.get(`/reports/${id}`);

export const exportReport = (id, format) =>
  api.get(`/reports/export/${format}/${id}`, { responseType: 'blob' });

export const getDashboard = (days = 14, months = 6) =>
  api.get('/dashboard/', { params: { days, months } });

export const getAuditLogs = (page = 1, pageSize = 20, filters = {}) =>
  api.get('/logs/', { params: { page, page_size: pageSize, ...filters } });

export default api;
