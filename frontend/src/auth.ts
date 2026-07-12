// Local-only session helper. Mocked against mockData.ts — no API calls yet.
import { authMock } from "./mock/mockData";

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

export function login(email: string, password: string): { user: SessionUser } | { error: string } {
  const match = authMock.users.find((u) => u.email.toLowerCase() === email.toLowerCase());
  if (!match || match.password !== password) {
    return { error: "Invalid credentials" };
  }
  const { password: _password, ...user } = match;
  localStorage.setItem(TOKEN_KEY, `mock.${user.id}.${Date.now()}`);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  return { user };
}

export function signup(input: {
  full_name: string;
  email: string;
  password: string;
  role: string;
}): { user: SessionUser } | { error: string } {
  if (authMock.users.some((u) => u.email.toLowerCase() === input.email.toLowerCase())) {
    return { error: "An account with this email already exists" };
  }
  const user: SessionUser = {
    id: Math.max(...authMock.users.map((u) => u.id)) + 1,
    email: input.email,
    full_name: input.full_name,
    role: input.role,
    department_id: 1,
    points_balance: 0,
  };
  localStorage.setItem(TOKEN_KEY, `mock.${user.id}.${Date.now()}`);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  return { user };
}

export function logout(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}
