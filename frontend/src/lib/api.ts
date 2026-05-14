import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

// Attach JWT from localStorage
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Auto-redirect on 401
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default api;

// Typed API helpers
export const storyApi = {
  run: (query: string) => api.post("/stories/run", { query }),
  list: (limit = 20, offset = 0) => api.get(`/stories?limit=${limit}&offset=${offset}`),
  get: (id: string) => api.get(`/stories/${id}`),
  getByRunId: (runId: string) => api.get(`/stories/run/${runId}`),
  trending: () => api.get("/stories/trending"),
  approve: (runId: string, notes = "") => api.post(`/stories/${runId}/approve`, { notes }),
  reject: (runId: string, reason: string) => api.post(`/stories/${runId}/reject`, { reason }),
  publish: (runId: string, targets: unknown[]) => api.post(`/stories/${runId}/publish`, { targets }),
};

export const authApi = {
  login: (email: string, password: string) => api.post("/auth/login", { email, password }),
  register: (email: string, password: string, full_name: string) =>
    api.post("/auth/register", { email, password, full_name }),
  me: () => api.get("/auth/me"),
};

export const socialApi = {
  list: () => api.get("/social-accounts"),
  authUrl: () => api.get("/social-accounts/meta/auth-url"),
  disconnect: (id: string) => api.delete(`/social-accounts/${id}`),
};
