export type Role = "owner" | "admin" | "member";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  created_at: string;
}

export interface MeResponse {
  user: UserResponse;
  organization_id: string;
  role: Role;
}

export interface OrganizationResponse {
  id: string;
  name: string;
  created_at: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
  organization_name: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}
