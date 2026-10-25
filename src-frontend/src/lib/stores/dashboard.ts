import { get, writable } from 'svelte/store';
import { api } from '$lib/api/commands';
import { ApiError } from '$lib/api/client';
import type { DashboardFilters, DashboardResponse, PeriodKey } from '$lib/api/types';
import { authToken } from './auth';

export const dashboard = writable<DashboardResponse | null>(null);
export const dashboardLoading = writable(false);
export const dashboardError = writable<string | null>(null);
export const dashboardPeriod = writable<PeriodKey>('this_month');
export const dashboardWalletIds = writable<string[]>([]);
export const dashboardCustomRange = writable<{ from: string; to: string }>({
  from: '',
  to: ''
});

let requestId = 0;

function messageOf(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return error instanceof Error ? error.message : 'Gagal memuat ringkasan.';
}

export async function loadDashboard(filters?: Partial<DashboardFilters>): Promise<void> {
  const token = get(authToken);
  if (!token) return;

  const period = filters?.period ?? get(dashboardPeriod);
  const custom = get(dashboardCustomRange);
  const walletIds = filters?.wallet_ids ?? get(dashboardWalletIds);
  const request: DashboardFilters = {
    period,
    wallet_ids: walletIds,
    date_from: period === 'custom' ? custom.from : null,
    date_to: period === 'custom' ? custom.to : null
  };

  const current = ++requestId;
  dashboardLoading.set(true);
  dashboardError.set(null);

  try {
    const response = await api.dashboard(token, request);
    if (current === requestId) dashboard.set(response);
  } catch (error) {
    if (current === requestId) dashboardError.set(messageOf(error));
  } finally {
    if (current === requestId) dashboardLoading.set(false);
  }
}

export async function setDashboardPeriod(period: PeriodKey): Promise<void> {
  dashboardPeriod.set(period);
  await loadDashboard({ period });
}

export function resetDashboard(): void {
  dashboard.set(null);
  dashboardError.set(null);
  dashboardLoading.set(false);
  dashboardPeriod.set('this_month');
  dashboardWalletIds.set([]);
}
