import { get, writable } from 'svelte/store';
import { api } from '$lib/api/commands';
import type { SystemStatus } from '$lib/api/types';

export const systemStatus = writable<SystemStatus | null>(null);
export const systemLoading = writable(false);
export const systemError = writable<string | null>(null);

let timer: ReturnType<typeof setInterval> | null = null;
let inFlight = false;

export async function loadSystemStatus(): Promise<void> {
  if (inFlight) return;
  inFlight = true;
  systemLoading.set(true);
  try {
    const status = await api.systemStatus();
    systemStatus.set(status);
    systemError.set(null);
  } catch (error) {
    systemStatus.update((current) =>
      current
        ? { ...current, db_connected: false, offline: true, last_error: String(error) }
        : {
            app_version: '—',
            python_version: '—',
            db_connected: false,
            db_latency_ms: null,
            db_name: '—',
            db_uri_masked: null,
            config_source: 'unknown',
            data_dir: '—',
            last_error: error instanceof Error ? error.message : String(error),
            offline: true
          }
    );
    systemError.set(error instanceof Error ? error.message : String(error));
  } finally {
    systemLoading.set(false);
    inFlight = false;
  }
}

export function startSystemPolling(intervalMs = 30_000): () => void {
  void loadSystemStatus();
  if (timer) clearInterval(timer);
  timer = setInterval(() => void loadSystemStatus(), intervalMs);
  return () => {
    if (timer) clearInterval(timer);
    timer = null;
  };
}

export function getSystemStatus(): SystemStatus | null {
  return get(systemStatus);
}
