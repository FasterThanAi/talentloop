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

/**
 * Silent token refresh.
 *
 * Access tokens expire after 15 minutes. Previously a 401 was simply surfaced as an error,
 * so the app broke roughly a quarter of an hour into any session — /auth/me started
 * returning 401 while the UI still showed a logged-in user. Now a 401 triggers one refresh
 * attempt (the refresh token lives in an httpOnly cookie) and the original request is
 * replayed. Concurrent 401s share a single refresh so we don't stampede the endpoint.
 */
let refreshPromise = null;

const refreshAccessToken = async () => {
  if (!refreshPromise) {
    refreshPromise = axios
      .post(`${API_BASE_URL}/auth/refresh`, {}, { withCredentials: true })
      .then((res) => {
        const token = res.data?.access_token;
        if (!token) throw new Error("No access token in refresh response");
        localStorage.setItem("talentloop_token", token);
        if (res.data?.user) {
          localStorage.setItem("talentloop_user", JSON.stringify(res.data.user));
        }
        return token;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
};

// Response interceptor: refresh once on 401, then unwrap problem-detail error envelopes
api.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const original = error.config;
    const isAuthCall = original?.url?.includes("/auth/refresh") || original?.url?.includes("/auth/login");

    if (error.response?.status === 401 && original && !original._retried && !isAuthCall) {
      original._retried = true;
      try {
        const token = await refreshAccessToken();
        original.headers = { ...original.headers, Authorization: `Bearer ${token}` };
        return api.request(original);
      } catch {
        // Refresh itself failed — the session is genuinely over.
        localStorage.removeItem("talentloop_token");
        localStorage.removeItem("talentloop_user");
        if (!window.location.pathname.startsWith("/login")) {
          window.location.assign("/login?expired=1");
        }
      }
    }

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
