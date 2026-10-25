<script lang="ts">
  import { get } from 'svelte/store';
  import { api } from '$lib/api/commands';
  import { ApiError } from '$lib/api/client';
  import type { WalletType } from '$lib/api/types';
  import { authToken, currentUser } from '$lib/stores/auth';
  import { bumpData, closeWalletModal, pushToast, walletModal } from '$lib/stores/ui';
  import { loadWallets } from '$lib/stores/wallets';
  import Icon from './Icon.svelte';
  import MoneyInput from './MoneyInput.svelte';

  interface FormState {
    name: string;
    type: WalletType;
    initial_balance_cents: number;
    color: string;
    icon: string;
  }

  const COLORS = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#64748b'];
  const ICONS: Array<{ value: string; icon: 'wallet' | 'bank' | 'phone' | 'card' | 'chart' }> = [
    { value: 'wallet', icon: 'wallet' },
    { value: 'bank', icon: 'bank' },
    { value: 'phone', icon: 'phone' },
    { value: 'card', icon: 'card' },
    { value: 'chart', icon: 'chart' }
  ];
  const TYPES: Array<{ value: WalletType; label: string }> = [
    { value: 'cash', label: 'Tunai' },
    { value: 'bank', label: 'Bank' },
    { value: 'ewallet', label: 'E-Wallet' },
    { value: 'credit', label: 'Kartu Kredit' },
    { value: 'investment', label: 'Investasi' },
    { value: 'other', label: 'Lainnya' }
  ];

  let form = $state<FormState>({
    name: '',
    type: 'cash',
    initial_balance_cents: 0,
    color: COLORS[0],
    icon: 'wallet'
  });
  let saving = $state(false);
  let error = $state<string | null>(null);
  let initializedFor: string | null = null;

  const modal = $derived($walletModal);
  const editing = $derived(modal.wallet);
  const currency = $derived(editing?.currency ?? $currentUser?.base_currency ?? 'IDR');

  $effect(() => {
    const current = $walletModal;
    if (!current.open) {
      initializedFor = null;
      return;
    }
    const key = current.wallet?.id ?? 'new';
    if (initializedFor === key) return;
    initializedFor = key;

    form = {
      name: current.wallet?.name ?? '',
      type: current.wallet?.type ?? 'cash',
      initial_balance_cents: current.wallet?.initial_balance_cents ?? 0,
      color: current.wallet?.color ?? COLORS[0],
      icon: current.wallet?.icon ?? 'wallet'
    };
    error = null;
  });

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape' && modal.open && !saving) closeWalletModal();
  }

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    if (saving) return;

    const token = get(authToken);
    if (!token) {
      error = 'Sesi Anda sudah berakhir. Silakan masuk kembali.';
      return;
    }
    if (!form.name.trim()) {
      error = 'Nama dompet wajib diisi.';
      return;
    }

    saving = true;
    error = null;
    try {
      if (editing) {
        await api.updateWallet(token, {
          wallet_id: editing.id,
          name: form.name.trim(),
          type: form.type,
          initial_balance_cents: form.initial_balance_cents,
          color: form.color,
          icon: form.icon
        });
        pushToast('Dompet berhasil diperbarui.');
      } else {
        await api.createWallet(token, {
          name: form.name.trim(),
          type: form.type,
          currency,
          initial_balance_cents: form.initial_balance_cents,
          color: form.color,
          icon: form.icon
        });
        pushToast('Dompet baru berhasil dibuat.');
      }
      closeWalletModal();
      bumpData();
      await loadWallets(true);
    } catch (caught) {
      error = caught instanceof ApiError ? caught.message : 'Gagal menyimpan dompet.';
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
      onclick={() => !saving && closeWalletModal()}
    ></button>

    <div
      class="modal-panel surface relative max-h-[92vh] w-full max-w-md overflow-y-auto p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="wallet-modal-title"
    >
      <div class="flex items-start justify-between gap-4">
        <div class="flex items-center gap-3">
          <span class="grid size-10 place-items-center rounded-2xl bg-primary/12 text-primary">
            <Icon name={editing ? 'edit' : 'wallet-add'} size={19} />
          </span>
          <div>
            <h2 id="wallet-modal-title" class="text-lg font-semibold tracking-tight">
              {editing ? 'Ubah dompet' : 'Dompet baru'}
            </h2>
            <p class="text-xs text-base-content/45">
              {editing ? 'Perbarui informasi dompet Anda' : 'Tambahkan sumber dana baru'}
            </p>
          </div>
        </div>
        <button
          type="button"
          class="btn btn-ghost btn-sm btn-circle"
          aria-label="Tutup"
          disabled={saving}
          onclick={closeWalletModal}
        >
          <Icon name="close" size={18} />
        </button>
      </div>

      <form class="mt-6 space-y-4" onsubmit={handleSubmit}>
        <label class="block">
          <span class="mb-1.5 block text-xs font-medium text-base-content/60">Nama dompet</span>
          <input
            type="text"
            class="input input-bordered w-full"
            placeholder="Mis. Dompet Tunai, Bank BCA…"
            maxlength="60"
            bind:value={form.name}
            required
          />
        </label>

        <div class="grid gap-4 sm:grid-cols-2">
          <label class="block">
            <span class="mb-1.5 block text-xs font-medium text-base-content/60">Jenis</span>
            <select class="select select-bordered w-full" bind:value={form.type}>
              {#each TYPES as type (type.value)}
                <option value={type.value}>{type.label}</option>
              {/each}
            </select>
          </label>

          <div>
            <span class="mb-1.5 block text-xs font-medium text-base-content/60">Ikon</span>
            <div class="flex gap-1.5">
              {#each ICONS as option (option.value)}
                <button
                  type="button"
                  class="btn btn-sm btn-square {form.icon === option.value
                    ? 'btn-primary'
                    : 'btn-ghost bg-base-200'}"
                  aria-label={`Ikon ${option.value}`}
                  aria-pressed={form.icon === option.value}
                  onclick={() => (form.icon = option.value)}
                >
                  <Icon name={option.icon} size={16} />
                </button>
              {/each}
            </div>
          </div>
        </div>

        <div>
          <span class="mb-1.5 block text-xs font-medium text-base-content/60">Saldo awal</span>
          <MoneyInput bind:value={form.initial_balance_cents} currency={currency} id="wallet-balance" />
          <p class="mt-1 text-[11px] text-base-content/40">
            Saldo saat ini dihitung otomatis dari saldo awal + pemasukan − pengeluaran.
          </p>
        </div>

        <div>
          <span class="mb-1.5 block text-xs font-medium text-base-content/60">Warna</span>
          <div class="flex flex-wrap gap-2">
            {#each COLORS as color (color)}
              <button
                type="button"
                class="size-8 rounded-full border-2 transition-transform hover:scale-110 {form.color === color
                  ? 'border-base-content/70 ring-2 ring-base-content/10'
                  : 'border-transparent'}"
                style={`background-color: ${color}`}
                aria-label={`Warna ${color}`}
                aria-pressed={form.color === color}
                onclick={() => (form.color = color)}
              ></button>
            {/each}
          </div>
        </div>

        {#if error}
          <div class="alert alert-error py-2 text-xs" role="alert">
            <Icon name="alert" size={15} />
            <span>{error}</span>
          </div>
        {/if}

        <div class="flex justify-end gap-2 border-t border-base-content/8 pt-4">
          <button type="button" class="btn btn-ghost" disabled={saving} onclick={closeWalletModal}>
            Batal
          </button>
          <button type="submit" class="btn btn-primary min-w-28" disabled={saving}>
            {#if saving}
              <span class="loading loading-spinner loading-xs"></span>
            {/if}
            {editing ? 'Simpan perubahan' : 'Buat dompet'}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}
