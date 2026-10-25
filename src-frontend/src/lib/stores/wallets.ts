import { get, writable } from 'svelte/store';
import { api } from '$lib/api/commands';
import { ApiError } from '$lib/api/client';
import type { Wallet } from '$lib/api/types';
import { authToken } from './auth';

export const wallets = writable<Wallet[]>([]);
export const totalBalance = writable(0);
export const walletsLoading = writable(false);
export const walletsError = writable<string | null>(null);
export const walletsLoaded = writable(false);

let inFlight: Promise<void> | null = null;

function messageOf(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return error instanceof Error ? error.message : 'Gagal memuat dompet.';
}

export async function loadWallets(force = false): Promise<void> {
  if (!force && get(walletsLoaded)) return;
  if (inFlight) return inFlight;

  const token = get(authToken);
  if (!token) return;

  walletsLoading.set(true);
  walletsError.set(null);

  inFlight = (async () => {
    try {
      const response = await api.listWallets(token);
      wallets.set(response.wallets);
      totalBalance.set(response.total_balance_cents);
      walletsLoaded.set(true);
    } catch (error) {
      walletsError.set(messageOf(error));
    } finally {
      walletsLoading.set(false);
      inFlight = null;
    }
  })();

  return inFlight;
}

export function upsertWallet(wallet: Wallet): void {
  wallets.update((items) => {
    const index = items.findIndex((item) => item.id === wallet.id);
    if (index === -1) return [...items, wallet];
    const next = [...items];
    next[index] = wallet;
    return next;
  });
  wallets.update((items) => {
    totalBalance.set(
      items.filter((item) => !item.archived).reduce((sum, item) => sum + item.balance_cents, 0)
    );
    return items;
  });
}

export function removeWallet(walletId: string): void {
  wallets.update((items) => items.filter((item) => item.id !== walletId));
  wallets.update((items) => {
    totalBalance.set(
      items.filter((item) => !item.archived).reduce((sum, item) => sum + item.balance_cents, 0)
    );
    return items;
  });
}

export function resetWallets(): void {
  wallets.set([]);
  totalBalance.set(0);
  walletsLoaded.set(false);
  walletsError.set(null);
  inFlight = null;
}
