<script lang="ts">
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { api } from '$lib/api/commands';
  import type { CategoriesResponse, Transaction } from '$lib/api/types';
  import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import FilterBar from '$lib/components/FilterBar.svelte';
  import Icon from '$lib/components/Icon.svelte';
  import TransactionTable from '$lib/components/TransactionTable.svelte';
  import { authToken, currentUser } from '$lib/stores/auth';
  import {
    loadTransactions,
    resetTransactionFilters,
    setTransactionPage,
    transactionFilters,
    transactions,
    transactionsError,
    transactionsLoading
  } from '$lib/stores/transactions';
  import {
    bumpData,
    onDataChange,
    openTransactionModal,
    pushToast
  } from '$lib/stores/ui';
  import { loadWallets, wallets } from '$lib/stores/wallets';
  import { formatMoney } from '$lib/utils/format';

  let categories = $state<CategoriesResponse>({ income: [], expense: [] });
  let deleteTarget = $state<Transaction | null>(null);
  let deleting = $state(false);

  const currency = $derived($currentUser?.base_currency ?? 'IDR');
  const response = $derived($transactions);
  const allCategories = $derived(
    Array.from(new Set([...categories.income, ...categories.expense])).sort((a, b) =>
      a.localeCompare(b, 'id')
    )
  );
  const hasFilters = $derived(
    $transactionFilters.search.trim().length > 0 ||
      $transactionFilters.types.length > 0 ||
      $transactionFilters.wallet_ids.length > 0 ||
      $transactionFilters.categories.length > 0 ||
      $transactionFilters.date_from !== null ||
      $transactionFilters.date_to !== null
  );
  const rangeStart = $derived(
    response && response.total > 0 ? (response.page - 1) * response.page_size + 1 : 0
  );
  const rangeEnd = $derived(
    response ? Math.min(response.page * response.page_size, response.total) : 0
  );

  onMount(() => {
    void loadWallets();
    void loadTransactions();
    const token = get(authToken);
    if (token) {
      void api
        .categories(token)
        .then((result) => (categories = result))
        .catch(() => undefined);
    }
    return onDataChange(() => {
      void loadTransactions();
      void loadWallets(true);
    });
  });

  function handleFilterChange(patch: Parameters<typeof loadTransactions>[0]) {
    void loadTransactions(patch);
  }

  function requestDelete(transaction: Transaction) {
    deleteTarget = transaction;
  }

  function cancelDelete() {
    if (deleting) return;
    deleteTarget = null;
  }

  async function performDelete() {
    const token = get(authToken);
    if (!token || !deleteTarget || deleting) return;
    deleting = true;
    try {
      await api.deleteTransaction(token, deleteTarget.id);
      pushToast('Transaksi berhasil dihapus.');
      deleteTarget = null;
      bumpData();
      await Promise.all([loadTransactions(), loadWallets(true)]);
    } catch (caught) {
      pushToast(caught instanceof Error ? caught.message : 'Gagal menghapus transaksi.', 'error');
    } finally {
      deleting = false;
    }
  }

  async function handleReset() {
    await resetTransactionFilters();
  }
</script>

<div class="space-y-5">
  <header class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
    <div>
      <h2 class="text-2xl font-semibold tracking-tight">Transaksi</h2>
      <p class="mt-1 text-sm text-base-content/45">
        Telusuri, filter, dan kelola seluruh riwayat keuangan Anda.
      </p>
    </div>
    <button
      type="button"
      class="btn btn-primary"
      onclick={() => openTransactionModal({ defaultType: 'expense' })}
    >
      <Icon name="plus" size={17} />
      Tambah transaksi
    </button>
  </header>

  <div class="grid gap-3 sm:grid-cols-3">
    <div class="surface flex items-center justify-between p-4">
      <div>
        <p class="text-[10px] font-semibold uppercase tracking-wider text-base-content/40">Hasil</p>
        <p class="tabular mt-1 text-xl font-semibold">{response?.total ?? 0}</p>
      </div>
      <span class="grid size-9 place-items-center rounded-xl bg-base-200 text-base-content/45">
        <Icon name="transactions" size={17} />
      </span>
    </div>
    <div class="surface flex items-center justify-between p-4">
      <div>
        <p class="text-[10px] font-semibold uppercase tracking-wider text-base-content/40">
          Pemasukan
        </p>
        <p class="tabular mt-1 text-xl font-semibold text-success">
          {formatMoney(response?.income_cents ?? 0, currency)}
        </p>
      </div>
      <span class="grid size-9 place-items-center rounded-xl bg-success/12 text-success">
        <Icon name="arrow-up" size={17} />
      </span>
    </div>
    <div class="surface flex items-center justify-between p-4">
      <div>
        <p class="text-[10px] font-semibold uppercase tracking-wider text-base-content/40">
          Pengeluaran
        </p>
        <p class="tabular mt-1 text-xl font-semibold text-error">
          {formatMoney(response?.expense_cents ?? 0, currency)}
        </p>
      </div>
      <span class="grid size-9 place-items-center rounded-xl bg-error/12 text-error">
        <Icon name="arrow-down" size={17} />
      </span>
    </div>
  </div>

  <FilterBar
    filters={$transactionFilters}
    wallets={$wallets}
    categories={allCategories}
    onchange={handleFilterChange}
    onreset={handleReset}
  />

  {#if $transactionsError}
    <div class="alert alert-error text-sm" role="alert">
      <Icon name="alert" size={17} />
      <span>{$transactionsError}</span>
      <button type="button" class="btn btn-ghost btn-xs" onclick={() => void loadTransactions()}>
        Coba lagi
      </button>
    </div>
  {/if}

  <section class="surface overflow-hidden">
    {#if $transactionsLoading && !response}
      <div class="space-y-4 p-5">
        {#each [0, 1, 2, 3, 4] as item (item)}
          <div class="flex items-center gap-3">
            <div class="skeleton size-9 rounded-xl"></div>
            <div class="flex-1 space-y-2">
              <div class="skeleton h-3 w-36 rounded"></div>
              <div class="skeleton h-2.5 w-24 rounded"></div>
            </div>
            <div class="skeleton h-3 w-24 rounded"></div>
          </div>
        {/each}
      </div>
    {:else if response && response.items.length > 0}
      <div class="relative">
        {#if $transactionsLoading}
          <div class="absolute inset-x-0 top-0 z-10 h-0.5 overflow-hidden bg-primary/10">
            <div class="h-full w-1/3 animate-pulse bg-primary"></div>
          </div>
        {/if}
        <TransactionTable
          items={response.items}
          {currency}
          onedit={(transaction) => openTransactionModal({ transaction })}
          ondelete={requestDelete}
          busyId={deleting ? deleteTarget?.id ?? null : null}
        />
      </div>

      <div
        class="flex flex-col items-center justify-between gap-3 border-t border-base-content/8 px-5 py-3 sm:flex-row"
      >
        <p class="text-[11px] text-base-content/45">
          Menampilkan {rangeStart}–{rangeEnd} dari {response.total} transaksi
        </p>
        <div class="flex items-center gap-1">
          <button
            type="button"
            class="btn btn-ghost btn-xs"
            disabled={response.page <= 1 || $transactionsLoading}
            onclick={() => void setTransactionPage(response.page - 1)}
          >
            <Icon name="chevron-left" size={14} />
            Sebelumnya
          </button>
          <span class="px-2 text-[11px] font-medium text-base-content/55">
            {response.page} / {Math.max(response.pages, 1)}
          </span>
          <button
            type="button"
            class="btn btn-ghost btn-xs"
            disabled={response.page >= response.pages || $transactionsLoading}
            onclick={() => void setTransactionPage(response.page + 1)}
          >
            Berikutnya
            <Icon name="chevron-right" size={14} />
          </button>
        </div>
      </div>
    {:else}
      <EmptyState
        icon={hasFilters ? 'alert' : 'transactions'}
        title={hasFilters ? 'Tidak ada hasil' : 'Belum ada transaksi'}
        description={hasFilters
          ? 'Tidak ada transaksi yang cocok dengan filter Anda. Coba ubah kata kunci atau rentang tanggal.'
          : 'Mulai catat pemasukan dan pengeluaran agar riwayat keuangan Anda terlihat di sini.'}
      >
        {#if hasFilters}
          <button type="button" class="btn btn-ghost btn-sm" onclick={handleReset}>
            <Icon name="refresh" size={15} />
            Reset filter
          </button>
        {:else}
          <button
            type="button"
            class="btn btn-primary btn-sm"
            onclick={() => openTransactionModal({ defaultType: 'expense' })}
          >
            <Icon name="plus" size={15} />
            Tambah transaksi
          </button>
        {/if}
      </EmptyState>
    {/if}
  </section>
</div>

<ConfirmDialog
  open={deleteTarget !== null}
  title="Hapus transaksi?"
  message={deleteTarget
    ? `Transaksi "${deleteTarget.category}" sebesar ${formatMoney(
        deleteTarget.amount_cents,
        currency
      )} akan dihapus permanen.`
    : ''}
  busy={deleting}
  onconfirm={performDelete}
  oncancel={cancelDelete}
/>
