import { api } from "@/lib/api";
import { tokenStorage } from "@/lib/token-storage";
import type {
  LoginPayload,
  MeResponse,
  OrganizationResponse,
  RegisterPayload,
  TokenResponse,
} from "@/types/auth";

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const response = await api.post<TokenResponse>("/auth/login", payload);
  tokenStorage.setTokens(response.data.access_token, response.data.refresh_token);
  return response.data;
}

export async function register(payload: RegisterPayload): Promise<TokenResponse> {
  const response = await api.post<TokenResponse>("/auth/register", payload);
  tokenStorage.setTokens(response.data.access_token, response.data.refresh_token);
  return response.data;
}

export async function logout(): Promise<void> {
  const refreshToken = tokenStorage.getRefreshToken();
  tokenStorage.clear();
  if (refreshToken) {
    // Best-effort — the client-side session is already cleared either way.
    await api.post("/auth/logout", { refresh_token: refreshToken }).catch(() => undefined);
  }
}

export async function getMe(): Promise<MeResponse> {
  const response = await api.get<MeResponse>("/me");
  return response.data;
}

export async function getCurrentOrganization(): Promise<OrganizationResponse> {
  const response = await api.get<OrganizationResponse>("/organizations/current");
  return response.data;
}
