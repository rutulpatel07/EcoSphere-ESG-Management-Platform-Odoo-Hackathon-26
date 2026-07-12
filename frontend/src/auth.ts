// Session helper. Login calls the real POST /auth/login per docs/CONTRACT.md.
//
// Signup stays mock-only: CONTRACT.md defines no public self-registration route
// (POST /users exists but is an authenticated admin-management endpoint, not
// usable by an anonymous visitor creating their own account). See the report
// delivered alongside this wiring for details.
import { AuthApi } from "./api/endpoints";
import { authMock } from "./mock/mockData";
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

// No contract endpoint for self-service signup — kept local/mock, not wired to the API.
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
