export type UserRole = "ADMIN" | "STAFF";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  permissions: string[];
}

export interface LoginApiResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

export interface AuthSession {
  accessToken: string;
  user: AuthUser;
}
