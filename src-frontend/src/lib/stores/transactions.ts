import { get, writable } from 'svelte/store';
import { api } from '$lib/api/commands';
import { ApiError } from '$lib/api/client';
import type { TransactionFilters, TransactionListResponse } from '$lib/api/types';
import { authToken } from './auth';

export const defaultFilters: TransactionFilters = {
  wallet_ids: [],
  types: [],
  categories: [],
  date_from: null,
  date_to: null,
  search: '',
  page: 1,
  page_size: 25,
  sort_by: 'occurred_at',
  sort_dir: 'desc'
};

export const transactions = writable<TransactionListResponse | null>(null);
export const transactionFilters = writable<TransactionFilters>({ ...defaultFilters });
export const transactionsLoading = writable(false);
export const transactionsError = writable<string | null>(null);

let requestId = 0;

function messageOf(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return error instanceof Error ? error.message : 'Gagal memuat transaksi.';
}

export async function loadTransactions(patch?: Partial<TransactionFilters>): Promise<void> {
  const token = get(authToken);
  if (!token) return;

  const filters: TransactionFilters = { ...get(transactionFilters), ...patch };
  transactionFilters.set(filters);

  const current = ++requestId;
  transactionsLoading.set(true);
  transactionsError.set(null);

  try {
    const response = await api.listTransactions(token, filters);
    if (current === requestId) transactions.set(response);
  } catch (error) {
    if (current === requestId) transactionsError.set(messageOf(error));
  } finally {
    if (current === requestId) transactionsLoading.set(false);
  }
}

export async function setTransactionPage(page: number): Promise<void> {
  await loadTransactions({ page });
}

export async function resetTransactionFilters(): Promise<void> {
  transactionFilters.set({ ...defaultFilters });
  await loadTransactions();
}

export function resetTransactions(): void {
  transactions.set(null);
  transactionFilters.set({ ...defaultFilters });
  transactionsError.set(null);
  transactionsLoading.set(false);
}
