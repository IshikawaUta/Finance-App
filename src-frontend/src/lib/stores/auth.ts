import { derived, get, writable } from 'svelte/store';
import { api } from '$lib/api/commands';
import { ApiError } from '$lib/api/client';
import type { AuthResponse, LoginInput, RegisterInput, User } from '$lib/api/types';

const TOKEN_KEY = 'finance.token';
const USER_KEY = 'finance.user';

export const authToken = writable<string | null>(null);
export const currentUser = writable<User | null>(null);
export const authReady = writable(false);
export const authError = writable<string | null>(null);
export const isAuthenticated = derived(authToken, ($token) => Boolean($token));

let bootstrapped = false;

function persist(token: string, user: User): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } catch {
    // ignore storage failures
  }
}

function readStorage(): { token: string | null; user: User | null } {
  if (typeof localStorage === 'undefined') return { token: null, user: null };
  try {
    const token = localStorage.getItem(TOKEN_KEY);
    const rawUser = localStorage.getItem(USER_KEY);
    return {
      token,
      user: rawUser ? (JSON.parse(rawUser) as User) : null
    };
  } catch {
    return { token: null, user: null };
  }
}

export function applySession(session: AuthResponse): void {
  authToken.set(session.token);
  currentUser.set(session.user);
  persist(session.token, session.user);
}

export function clearSession(): void {
  authToken.set(null);
  currentUser.set(null);
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  } catch {
    // ignore
  }
}

export async function bootstrapAuth(): Promise<void> {
  if (bootstrapped) return;
  bootstrapped = true;

  const stored = readStorage();
  authToken.set(stored.token);
  if (stored.user) currentUser.set(stored.user);

  if (!stored.token) {
    authReady.set(true);
    return;
  }

  try {
    const user = await api.me(stored.token);
    currentUser.set(user);
    persist(stored.token, user);
  } catch (error) {
    // Keep the cached session when the database is offline; only discard it
    // when the backend explicitly says the token is invalid/expired.
    if (error instanceof ApiError && error.code.startsWith('AUTH_')) {
      clearSession();
    }
  } finally {
    authReady.set(true);
  }
}

export async function login(input: LoginInput): Promise<void> {
  authError.set(null);
  try {
    const session = await api.login(input);
    applySession(session);
  } catch (error) {
    authError.set(error instanceof Error ? error.message : 'Gagal masuk.');
    throw error;
  }
}

export async function register(input: RegisterInput): Promise<void> {
  authError.set(null);
  try {
    const session = await api.register(input);
    applySession(session);
  } catch (error) {
    authError.set(error instanceof Error ? error.message : 'Gagal mendaftar.');
    throw error;
  }
}

export async function logout(): Promise<void> {
  const token = get(authToken);
  clearSession();
  if (token) {
    try {
      await api.logout(token);
    } catch {
      // Local logout must always succeed.
    }
  }
}

export function resetAuthBootstrap(): void {
  bootstrapped = false;
  authReady.set(false);
}
