import { writable, get } from 'svelte/store';
import type { Transaction, TransactionType, Wallet } from '$lib/api/types';

export type Theme = 'light' | 'dark';
export type ToastKind = 'success' | 'error' | 'info';

export interface Toast {
  id: number;
  kind: ToastKind;
  message: string;
}

const THEME_KEY = 'finance.theme';

export const theme = writable<Theme>('light');
export const toasts = writable<Toast[]>([]);

export const dataRevision = writable(0);

export const transactionModal = writable<{
  open: boolean;
  transaction: Transaction | null;
  defaultType: TransactionType;
}>({ open: false, transaction: null, defaultType: 'expense' });

export const walletModal = writable<{ open: boolean; wallet: Wallet | null }>({
  open: false,
  wallet: null
});

export function initTheme(): void {
  if (typeof document === 'undefined') return;
  const current = document.documentElement.dataset.theme;
  const next: Theme = current === 'dark' ? 'dark' : 'light';
  theme.set(next);
  document.documentElement.dataset.theme = next;
}

export function setTheme(next: Theme): void {
  theme.set(next);
  if (typeof document !== 'undefined') {
    document.documentElement.dataset.theme = next;
  }
  try {
    localStorage.setItem(THEME_KEY, next);
  } catch {
    // localStorage can be unavailable in hardened webviews
  }
}

export function toggleTheme(): void {
  setTheme(get(theme) === 'dark' ? 'light' : 'dark');
}

let toastId = 0;

export function pushToast(message: string, kind: ToastKind = 'success'): void {
  const id = ++toastId;
  toasts.update((items) => [...items, { id, kind, message }]);
  setTimeout(() => dismissToast(id), 4600);
}

export function dismissToast(id: number): void {
  toasts.update((items) => items.filter((item) => item.id !== id));
}

export function bumpData(): void {
  dataRevision.update((value) => value + 1);
}

/** Subscribe to mutations, skipping the initial subscription call. */
export function onDataChange(callback: () => void): () => void {
  let first = true;
  return dataRevision.subscribe(() => {
    if (first) {
      first = false;
      return;
    }
    callback();
  });
}

export function openTransactionModal(options?: {
  transaction?: Transaction | null;
  defaultType?: TransactionType;
}): void {
  transactionModal.set({
    open: true,
    transaction: options?.transaction ?? null,
    defaultType: options?.defaultType ?? 'expense'
  });
}

export function closeTransactionModal(): void {
  transactionModal.update((state) => ({ ...state, open: false }));
}

export function openWalletModal(wallet: Wallet | null = null): void {
  walletModal.set({ open: true, wallet });
}

export function closeWalletModal(): void {
  walletModal.update((state) => ({ ...state, open: false }));
}
