import axios from 'axios';

// Use environment variable or fallback to remote MCP server
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://149.102.158.71:8090/api';
// Backend server URL
const BACKEND_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://149.102.158.71:4797/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 10000, // 10 second timeout
});

// Backend API instance for non-MCP calls
export const backendApi = axios.create({
  baseURL: BACKEND_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 60000, // 60 second timeout for backend operations
});

// Export URLs for components that need direct access
export const API_URL = API_BASE_URL;
export const BACKEND_URL = BACKEND_BASE_URL;

// Auth interceptor for MCP API
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && !err.config?.url?.includes('/auth/login')) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// Auth interceptor for Backend API
backendApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

backendApi.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && !err.config?.url?.includes('/auth/login')) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export default api;
