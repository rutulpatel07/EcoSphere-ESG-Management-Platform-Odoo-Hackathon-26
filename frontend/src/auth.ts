// Session helper. Login and signup both call the real backend
// (POST /auth/login, POST /auth/signup).
import { AuthApi } from "./api/endpoints";
import { describeApiError } from "./hooks/useApi";

export interface SessionUser {
  id: number;
  email: string;
  full_name: string;
  role: string;
  department_id: number;
  points_balance: number;
}

const TOKEN_KEY = "ecosphere_token";
const USER_KEY = "ecosphere_user";

export function getSessionUser(): SessionUser | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as SessionUser;
  } catch {
    return null;
  }
}

export function isAuthenticated(): boolean {
  return Boolean(localStorage.getItem(TOKEN_KEY));
}

// Server enforces these same role checks on every guarded route (403 if violated) —
// these helpers exist so the UI can hide actions that would otherwise 403, not as
// a security boundary of their own.
export function isManager(user: SessionUser | null): boolean {
  return user?.role === "ADMIN" || user?.role === "MANAGER";
}

export function isAdmin(user: SessionUser | null): boolean {
  return user?.role === "ADMIN";
}

export async function login(email: string, password: string): Promise<{ user: SessionUser } | { error: string } > {
  try {
    const res = await AuthApi.login(email, password);
    localStorage.setItem(TOKEN_KEY, res.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(res.user));
    return { user: res.user };
  } catch (err) {
    return { error: describeApiError(err) };
  }
}

// Signup always creates an EMPLOYEE — the backend accepts no role field on
// POST /auth/signup (role is never client-controlled at account creation).
export async function signup(input: {
  full_name: string;
  email: string;
  password: string;
  department_id?: number | null;
}): Promise<{ user: SessionUser } | { error: string }> {
  try {
    const res = await AuthApi.signup(input);
    localStorage.setItem(TOKEN_KEY, res.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(res.user));
    return { user: res.user };
  } catch (err) {
    return { error: describeApiError(err) };
  }
}

export function logout(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}
