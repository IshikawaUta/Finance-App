<script lang="ts">
  import type { Wallet } from '$lib/api/types';
  import { formatMoney } from '$lib/utils/format';
  import Icon from './Icon.svelte';

  let {
    wallet,
    onedit,
    ondelete
  }: {
    wallet: Wallet;
    onedit: (wallet: Wallet) => void;
    ondelete: (wallet: Wallet) => void;
  } = $props();

  const typeMeta: Record<string, { label: string; icon: 'wallet' | 'bank' | 'phone' | 'card' | 'chart' }> =
    {
      cash: { label: 'Tunai', icon: 'wallet' },
      bank: { label: 'Bank', icon: 'bank' },
      ewallet: { label: 'E-Wallet', icon: 'phone' },
      credit: { label: 'Kartu Kredit', icon: 'card' },
      investment: { label: 'Investasi', icon: 'chart' },
      other: { label: 'Lainnya', icon: 'wallet' }
    };

  const meta = $derived(typeMeta[wallet.type] ?? typeMeta.other);
  const gradient = $derived(
    `linear-gradient(135deg, ${wallet.color}2e 0%, ${wallet.color}0a 55%, transparent 100%)`
  );
</script>

<article class="surface surface-hover relative overflow-hidden p-5">
  <div class="pointer-events-none absolute inset-0" style={gradient} aria-hidden="true"></div>
  <div class="relative">
    <div class="flex items-start justify-between gap-3">
      <div class="flex items-center gap-3">
        <span
          class="grid size-10 place-items-center rounded-xl text-white shadow-sm"
          style={`background-color: ${wallet.color}`}
        >
          <Icon name={meta.icon} size={18} />
        </span>
        <div>
          <h3 class="max-w-[11rem] truncate text-sm font-semibold">{wallet.name}</h3>
          <p class="text-[11px] font-medium uppercase tracking-wider text-base-content/40">
            {meta.label} · {wallet.currency}
          </p>
        </div>
      </div>
      <div class="flex items-center gap-1">
        <button
          type="button"
          class="btn btn-ghost btn-xs btn-circle text-base-content/40 hover:text-primary"
          title="Ubah dompet"
          aria-label={`Ubah ${wallet.name}`}
          onclick={() => onedit(wallet)}
        >
          <Icon name="edit" size={15} />
        </button>
        <button
          type="button"
          class="btn btn-ghost btn-xs btn-circle text-base-content/40 hover:text-error"
          title="Hapus dompet"
          aria-label={`Hapus ${wallet.name}`}
          onclick={() => ondelete(wallet)}
        >
          <Icon name="trash" size={15} />
        </button>
      </div>
    </div>

    <div class="mt-6">
      <p class="text-[11px] font-medium uppercase tracking-wider text-base-content/40">Saldo saat ini</p>
      <p class="tabular mt-1 text-2xl font-semibold tracking-tight">
        {formatMoney(wallet.balance_cents, wallet.currency)}
      </p>
    </div>

    <div class="mt-4 flex items-center justify-between border-t border-base-content/8 pt-3">
      <span class="text-[11px] text-base-content/45">Saldo awal</span>
      <span class="tabular text-[11px] font-medium text-base-content/60">
        {formatMoney(wallet.initial_balance_cents, wallet.currency)}
      </span>
    </div>
  </div>
</article>
