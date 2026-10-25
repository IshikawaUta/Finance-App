<script lang="ts">
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { api } from '$lib/api/commands';
  import { ApiError } from '$lib/api/client';
  import type { Wallet } from '$lib/api/types';
  import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import Icon from '$lib/components/Icon.svelte';
  import WalletCard from '$lib/components/WalletCard.svelte';
  import { authToken, currentUser } from '$lib/stores/auth';
  import {
    bumpData,
    onDataChange,
    openWalletModal,
    pushToast
  } from '$lib/stores/ui';
  import {
    loadWallets,
    totalBalance,
    wallets,
    walletsError,
    walletsLoading
  } from '$lib/stores/wallets';
  import { formatMoney } from '$lib/utils/format';

  let deleteTarget = $state<Wallet | null>(null);
  let cascade = $state(false);
  let deleting = $state(false);

  const currency = $derived($currentUser?.base_currency ?? 'IDR');
  const total = $derived($totalBalance);

  onMount(() => {
    void loadWallets();
    return onDataChange(() => void loadWallets(true));
  });

  function requestDelete(wallet: Wallet) {
    deleteTarget = wallet;
    cascade = false;
  }

  function cancelDelete() {
    if (deleting) return;
    deleteTarget = null;
    cascade = false;
  }

  async function performDelete() {
    const token = get(authToken);
    if (!token || !deleteTarget || deleting) return;

    deleting = true;
    try {
      await api.deleteWallet(token, deleteTarget.id, cascade);
      pushToast('Dompet berhasil dihapus.');
      deleteTarget = null;
      cascade = false;
      bumpData();
      await loadWallets(true);
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === 'WALLET_NOT_EMPTY' && !cascade) {
        cascade = true;
        pushToast('Dompet masih memiliki transaksi. Konfirmasi sekali lagi untuk menghapus semuanya.', 'info');
      } else {
        pushToast(caught instanceof Error ? caught.message : 'Gagal menghapus dompet.', 'error');
      }
    } finally {
      deleting = false;
    }
  }

  const confirmMessage = $derived(
    deleteTarget
      ? cascade
        ? `Dompet "${deleteTarget.name}" beserta seluruh transaksinya akan dihapus permanen. Tindakan ini tidak dapat dibatalkan.`
        : `Hapus dompet "${deleteTarget.name}"? Jika dompet masih memiliki transaksi, Anda akan diminta konfirmasi tambahan.`
      : ''
  );
</script>

<div class="space-y-5">
  <header class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
    <div>
      <h2 class="text-2xl font-semibold tracking-tight">Dompet</h2>
      <p class="mt-1 text-sm text-base-content/45">
        Kelola sumber dana dan pantau saldo masing-masing.
      </p>
    </div>
    <button type="button" class="btn btn-primary" onclick={() => openWalletModal()}>
      <Icon name="plus" size={17} />
      Tambah dompet
    </button>
  </header>

  <section
    class="surface relative overflow-hidden bg-gradient-to-br from-primary/12 via-base-100 to-secondary/8 p-6"
  >
    <div class="pointer-events-none absolute -right-12 -top-16 size-56 rounded-full bg-primary/10 blur-3xl"></div>
    <div class="relative flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-base-content/45">
          Total saldo gabungan
        </p>
        <p class="tabular mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
          {formatMoney(total, currency)}
        </p>
        <p class="mt-2 text-xs text-base-content/45">
          Dihitung dari saldo awal ditambah seluruh pemasukan dan pengeluaran.
        </p>
      </div>
      <div class="flex items-center gap-3">
        <div class="rounded-2xl border border-base-content/8 bg-base-100/70 px-4 py-3">
          <p class="text-[10px] font-medium uppercase tracking-wider text-base-content/40">
            Dompet aktif
          </p>
          <p class="tabular mt-1 text-lg font-semibold">{$wallets.length}</p>
        </div>
        <div class="rounded-2xl border border-base-content/8 bg-base-100/70 px-4 py-3">
          <p class="text-[10px] font-medium uppercase tracking-wider text-base-content/40">
            Mata uang
          </p>
          <p class="mt-1 text-lg font-semibold">{currency}</p>
        </div>
      </div>
    </div>
  </section>

  {#if $walletsError}
    <div class="alert alert-error text-sm" role="alert">
      <Icon name="alert" size={17} />
      <span>{$walletsError}</span>
      <button type="button" class="btn btn-ghost btn-xs" onclick={() => void loadWallets(true)}>
        Coba lagi
      </button>
    </div>
  {/if}

  {#if $walletsLoading && $wallets.length === 0}
    <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {#each [0, 1, 2] as item (item)}
        <div class="surface p-5">
          <div class="flex items-center gap-3">
            <div class="skeleton size-10 rounded-xl"></div>
            <div class="space-y-2">
              <div class="skeleton h-3 w-28 rounded"></div>
              <div class="skeleton h-2.5 w-20 rounded"></div>
            </div>
          </div>
          <div class="skeleton mt-6 h-8 w-40 rounded-lg"></div>
          <div class="skeleton mt-4 h-3 w-24 rounded"></div>
        </div>
      {/each}
    </div>
  {:else if $wallets.length === 0}
    <div class="surface">
      <EmptyState
        icon="wallet"
        title="Belum ada dompet"
        description="Dompet adalah tempat Anda menyimpan uang: tunai, rekening bank, e-wallet, investasi, dan lainnya."
      >
        <button type="button" class="btn btn-primary" onclick={() => openWalletModal()}>
          <Icon name="plus" size={16} />
          Buat dompet pertama
        </button>
      </EmptyState>
    </div>
  {:else}
    <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {#each $wallets as wallet (wallet.id)}
        <WalletCard wallet={wallet} onedit={(item) => openWalletModal(item)} ondelete={requestDelete} />
      {/each}
    </div>
  {/if}
</div>

<ConfirmDialog
  open={deleteTarget !== null}
  title={cascade ? 'Hapus dompet dan transaksi?' : 'Hapus dompet?'}
  message={confirmMessage}
  confirmLabel={cascade ? 'Hapus semuanya' : 'Hapus'}
  busy={deleting}
  onconfirm={performDelete}
  oncancel={cancelDelete}
/>
