<script lang="ts">
  import { get } from 'svelte/store';
  import { onMount } from 'svelte';
  import { api } from '$lib/api/commands';
  import { ApiError } from '$lib/api/client';
  import type { CategoriesResponse, TransactionType } from '$lib/api/types';
  import { authToken } from '$lib/stores/auth';
  import {
    closeTransactionModal,
    bumpData,
    pushToast,
    transactionModal
  } from '$lib/stores/ui';
  import { wallets, loadWallets } from '$lib/stores/wallets';
  import { combineDateWithTime, toDateInputValue } from '$lib/utils/format';
  import Icon from './Icon.svelte';
  import MoneyInput from './MoneyInput.svelte';

  interface FormState {
    type: TransactionType;
    amount_cents: number;
    wallet_id: string;
    category: string;
    note: string;
    date: string;
  }

  let form = $state<FormState>({
    type: 'expense',
    amount_cents: 0,
    wallet_id: '',
    category: '',
    note: '',
    date: toDateInputValue()
  });
  let categories = $state<CategoriesResponse>({ income: [], expense: [] });
  let saving = $state(false);
  let error = $state<string | null>(null);
  let initializedFor: string | null = null;

  const modal = $derived($transactionModal);
  const editing = $derived(modal.transaction);
  const isIncome = $derived(form.type === 'income');
  const categoryOptions = $derived(isIncome ? categories.income : categories.expense);

  onMount(async () => {
    const token = get(authToken);
    if (!token) return;
    try {
      categories = await api.categories(token);
    } catch {
      categories = { income: [], expense: [] };
    }
  });

  $effect(() => {
    const current = $transactionModal;
    if (!current.open) {
      initializedFor = null;
      return;
    }

    const key = current.transaction?.id ?? `new-${current.defaultType}`;
    if (initializedFor === key) return;
    initializedFor = key;

    const transaction = current.transaction;
    form = {
      type: transaction?.type ?? current.defaultType,
      amount_cents: transaction?.amount_cents ?? 0,
      wallet_id: transaction?.wallet_id ?? ($wallets[0]?.id ?? ''),
      category: transaction?.category ?? '',
      note: transaction?.note ?? '',
      date: toDateInputValue(transaction?.occurred_at ?? new Date())
    };
    error = null;

    if ($wallets.length === 0) void loadWallets();
  });

  $effect(() => {
    if ($transactionModal.open && !form.wallet_id && $wallets.length > 0) {
      form.wallet_id = $wallets[0].id;
    }
  });

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape' && modal.open && !saving) closeTransactionModal();
  }

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    if (saving) return;

    const token = get(authToken);
    if (!token) {
      error = 'Sesi Anda sudah berakhir. Silakan masuk kembali.';
      return;
    }
    if (form.amount_cents <= 0) {
      error = 'Nominal harus lebih dari nol.';
      return;
    }
    if (!form.wallet_id) {
      error = 'Pilih dompet terlebih dahulu.';
      return;
    }
    if (!form.category.trim()) {
      error = 'Kategori wajib diisi.';
      return;
    }

    saving = true;
    error = null;
    const occurredAt = combineDateWithTime(form.date, editing?.occurred_at);

    try {
      if (editing) {
        await api.updateTransaction(token, {
          transaction_id: editing.id,
          wallet_id: form.wallet_id,
          type: form.type,
          amount_cents: form.amount_cents,
          category: form.category.trim(),
          note: form.note.trim(),
          occurred_at: occurredAt
        });
        pushToast('Transaksi berhasil diperbarui.');
      } else {
        await api.createTransaction(token, {
          wallet_id: form.wallet_id,
          type: form.type,
          amount_cents: form.amount_cents,
          category: form.category.trim(),
          note: form.note.trim(),
          occurred_at: occurredAt
        });
        pushToast(isIncome ? 'Pemasukan berhasil dicatat.' : 'Pengeluaran berhasil dicatat.');
      }
      closeTransactionModal();
      bumpData();
      void loadWallets(true);
    } catch (caught) {
      error = caught instanceof ApiError ? caught.message : 'Gagal menyimpan transaksi.';
    } finally {
      saving = false;
    }
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if modal.open}
  <div class="fixed inset-0 z-[100] grid place-items-center p-4">
    <button
      type="button"
      class="absolute inset-0 bg-black/50 backdrop-blur-sm"
      aria-label="Tutup dialog"
      onclick={() => !saving && closeTransactionModal()}
    ></button>

    <div
      class="modal-panel surface relative max-h-[92vh] w-full max-w-lg overflow-y-auto p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="transaction-modal-title"
    >
      <div class="flex items-start justify-between gap-4">
        <div class="flex items-center gap-3">
          <span
            class="grid size-10 place-items-center rounded-2xl {isIncome
              ? 'bg-success/12 text-success'
              : 'bg-error/12 text-error'}"
          >
            <Icon name={isIncome ? 'arrow-up' : 'arrow-down'} size={19} />
          </span>
          <div>
            <h2 id="transaction-modal-title" class="text-lg font-semibold tracking-tight">
              {editing ? 'Ubah transaksi' : 'Transaksi baru'}
            </h2>
            <p class="text-xs text-base-content/45">
              {editing ? 'Perbarui detail transaksi Anda' : 'Catat pemasukan atau pengeluaran'}
            </p>
          </div>
        </div>
        <button
          type="button"
          class="btn btn-ghost btn-sm btn-circle"
          aria-label="Tutup"
          disabled={saving}
          onclick={closeTransactionModal}
        >
          <Icon name="close" size={18} />
        </button>
      </div>

      <form class="mt-6 space-y-4" onsubmit={handleSubmit}>
        <div class="grid grid-cols-2 gap-2 rounded-xl bg-base-200 p-1">
          <button
            type="button"
            class="btn btn-sm border-0 {!isIncome
              ? 'bg-error text-error-content shadow-sm'
              : 'bg-transparent text-base-content/55 shadow-none hover:bg-base-300'}"
            onclick={() => (form.type = 'expense')}
          >
            <Icon name="arrow-down" size={15} />
            Pengeluaran
          </button>
          <button
            type="button"
            class="btn btn-sm border-0 {isIncome
              ? 'bg-success text-success-content shadow-sm'
              : 'bg-transparent text-base-content/55 shadow-none hover:bg-base-300'}"
            onclick={() => (form.type = 'income')}
          >
            <Icon name="arrow-up" size={15} />
            Pemasukan
          </button>
        </div>

        <div>
          <span class="mb-1.5 block text-xs font-medium text-base-content/60">Nominal</span>
          <MoneyInput bind:value={form.amount_cents} large placeholder="0" id="transaction-amount" />
        </div>

        <div class="grid gap-4 sm:grid-cols-2">
          <label class="block">
            <span class="mb-1.5 block text-xs font-medium text-base-content/60">Dompet</span>
            <select class="select select-bordered w-full" bind:value={form.wallet_id} disabled={$wallets.length === 0}>
              {#if $wallets.length === 0}
                <option value="">Belum ada dompet</option>
              {/if}
              {#each $wallets as wallet (wallet.id)}
                <option value={wallet.id}>{wallet.name}</option>
              {/each}
            </select>
          </label>

          <label class="block">
            <span class="mb-1.5 block text-xs font-medium text-base-content/60">Tanggal</span>
            <input type="date" class="input input-bordered w-full" bind:value={form.date} required />
          </label>
        </div>

        <label class="block">
          <span class="mb-1.5 block text-xs font-medium text-base-content/60">Kategori</span>
          <input
            type="text"
            class="input input-bordered w-full"
            placeholder="Pilih atau ketik kategori baru…"
            list="transaction-category-options"
            maxlength="40"
            bind:value={form.category}
            required
          />
          <datalist id="transaction-category-options">
            {#each categoryOptions as category (category)}
              <option value={category}></option>
            {/each}
          </datalist>
        </label>

        <label class="block">
          <span class="mb-1.5 block text-xs font-medium text-base-content/60"
            >Catatan <span class="font-normal text-base-content/35">(opsional)</span></span
          >
          <textarea
            class="textarea textarea-bordered min-h-20 w-full resize-none"
            placeholder="Mis. makan siang bersama tim"
            maxlength="280"
            bind:value={form.note}
          ></textarea>
        </label>

        {#if $wallets.length === 0}
          <div class="alert alert-warning py-2 text-xs">
            <Icon name="alert" size={15} />
            <span>Buat dompet terlebih dahulu di halaman Dompet sebelum mencatat transaksi.</span>
          </div>
        {/if}

        {#if error}
          <div class="alert alert-error py-2 text-xs" role="alert">
            <Icon name="alert" size={15} />
            <span>{error}</span>
          </div>
        {/if}

        <div class="flex justify-end gap-2 border-t border-base-content/8 pt-4">
          <button type="button" class="btn btn-ghost" disabled={saving} onclick={closeTransactionModal}>
            Batal
          </button>
          <button type="submit" class="btn btn-primary min-w-28" disabled={saving || $wallets.length === 0}>
            {#if saving}
              <span class="loading loading-spinner loading-xs"></span>
            {/if}
            {editing ? 'Simpan perubahan' : 'Simpan'}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}
