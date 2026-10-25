import { pyInvoke } from 'tauri-plugin-pytauri-api';
import type { ApiErrorPayload } from './types';

export class ApiError extends Error {
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(payload: ApiErrorPayload) {
    super(payload.message);
    this.name = 'ApiError';
    this.code = payload.code;
    this.details = payload.details ?? {};
  }
}

/** True when the app runs inside a Tauri webview (not a plain browser). */
export function isTauri(): boolean {
  if (typeof window === 'undefined') return false;
  return '__TAURI_INTERNALS__' in window || '__TAURI__' in window;
}

function parsePayload(raw: unknown): ApiErrorPayload | null {
  if (raw && typeof raw === 'object') {
    const candidate = raw as Partial<ApiErrorPayload>;
    if (typeof candidate.code === 'string' && typeof candidate.message === 'string') {
      return {
        code: candidate.code,
        message: candidate.message,
        details: candidate.details ?? {}
      };
    }
    return null;
  }
  if (typeof raw !== 'string') return null;

  try {
    const parsed = JSON.parse(raw) as Partial<ApiErrorPayload>;
    if (typeof parsed?.code === 'string' && typeof parsed?.message === 'string') {
      return { code: parsed.code, message: parsed.message, details: parsed.details ?? {} };
    }
  } catch {
    // Plain string rejection (pydantic validation, panics, etc.)
  }
  return null;
}

function normalizeError(raw: unknown): ApiError {
  const payload = parsePayload(raw);
  if (payload) return new ApiError(payload);

  const message =
    typeof raw === 'string'
      ? raw
      : raw instanceof Error
        ? raw.message
        : 'Terjadi kesalahan yang tidak diketahui.';

  const looksLikeValidation =
    message.toLowerCase().includes('validation error') ||
    message.toLowerCase().includes('validationerror');

  return new ApiError({
    code: looksLikeValidation ? 'VALIDATION_ERROR' : 'UNKNOWN',
    message: looksLikeValidation ? 'Data yang dikirim tidak valid.' : message
  });
}

/**
 * Single gateway for every backend call.
 *
 * - In Tauri it uses PyTauri's `pyInvoke` (JSON IPC).
 * - In a normal browser it lazily loads a localStorage-backed mock backend so
 *   the UI can be developed without Rust/Python.
 */
export async function invoke<T>(command: string, body?: unknown): Promise<T> {
  try {
    if (isTauri()) {
      return await pyInvoke<T>(command, body as never);
    }
    const { mockInvoke } = await import('./mock');
    return await mockInvoke<T>(command, body);
  } catch (error) {
    const apiError = normalizeError(error);
    if (
      typeof window !== 'undefined' &&
      ['AUTH_EXPIRED', 'AUTH_INVALID_TOKEN', 'AUTH_REQUIRED'].includes(apiError.code)
    ) {
      window.dispatchEvent(new CustomEvent('finance:unauthorized'));
    }
    throw apiError;
  }
}
