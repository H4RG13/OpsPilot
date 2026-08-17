import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import { config } from "@/app/config";
import { tokenStorage } from "@/lib/token-storage";

export const api = axios.create({
  baseURL: config.apiBaseUrl,
});

// Requests that must never trigger the refresh-and-retry flow below — a
// failed login/register is a normal form error, not an expired session.
const AUTH_ENDPOINTS = ["/auth/login", "/auth/register", "/auth/refresh"];

api.interceptors.request.use((requestConfig) => {
  const token = tokenStorage.getAccessToken();
  if (token) {
    requestConfig.headers.set("Authorization", `Bearer ${token}`);
  }
  return requestConfig;
});

type RetryableRequestConfig = InternalAxiosRequestConfig & { _retry?: boolean };

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = tokenStorage.getRefreshToken();
  if (!refreshToken) return null;

  try {
    const response = await axios.post<{ access_token: string; refresh_token: string }>(
      `${config.apiBaseUrl}/auth/refresh`,
      { refresh_token: refreshToken }
    );
    tokenStorage.setTokens(response.data.access_token, response.data.refresh_token);
    return response.data.access_token;
  } catch {
    tokenStorage.clear();
    return null;
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryableRequestConfig | undefined;
    const isAuthEndpoint = AUTH_ENDPOINTS.some((path) => originalRequest?.url?.includes(path));

    if (error.response?.status !== 401 || !originalRequest || originalRequest._retry || isAuthEndpoint) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;
    refreshPromise ??= refreshAccessToken().finally(() => {
      refreshPromise = null;
    });

    const newAccessToken = await refreshPromise;
    if (!newAccessToken) {
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
      return Promise.reject(error);
    }

    originalRequest.headers.set("Authorization", `Bearer ${newAccessToken}`);
    return api(originalRequest);
  }
);
