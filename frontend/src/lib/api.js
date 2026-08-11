import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
});

// Request interceptor to attach JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("talentloop_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor to unwrap problem-detail error envelopes
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response && error.response.data) {
      const errData = error.response.data;
      const normalizedError = new Error(errData.detail || errData.title || "An unexpected error occurred.");
      normalizedError.status = error.response.status;
      normalizedError.code = errData.code || `HTTP_${error.response.status}`;
      normalizedError.title = errData.title;
      normalizedError.problemDetail = errData;
      return Promise.reject(normalizedError);
    }
    return Promise.reject(error);
  }
);

export default api;
