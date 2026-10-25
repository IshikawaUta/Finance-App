<script lang="ts">
  import type { Transaction } from '$lib/api/types';
  import { formatDate, formatMoney } from '$lib/utils/format';
  import Icon from './Icon.svelte';

  let {
    items,
    currency = 'IDR',
    onedit,
    ondelete,
    busyId = null,
    compact = false
  }: {
    items: Transaction[];
    currency?: string;
    onedit: (transaction: Transaction) => void;
    ondelete?: (transaction: Transaction) => void;
    busyId?: string | null;
    compact?: boolean;
  } = $props();

  const palette = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#84cc16'];

  function categoryColor(category: string): string {
    let hash = 0;
    for (let index = 0; index < category.length; index += 1) {
      hash = (hash * 31 + category.charCodeAt(index)) >>> 0;
    }
    return palette[hash % palette.length];
  }

  function categoryInitial(category: string): string {
    return category.trim().charAt(0).toUpperCase() || '?';
  }
</script>

<div class="overflow-x-auto">
  <table class="table table-sm">
    <thead>
      <tr class="border-base-content/8 text-[10px] uppercase tracking-[0.12em] text-base-content/40">
        <th class="bg-transparent font-semibold">Transaksi</th>
        {#if !compact}
          <th class="hidden bg-transparent font-semibold md:table-cell">Dompet</th>
        {/if}
        <th class="hidden bg-transparent font-semibold sm:table-cell">Tanggal</th>
        <th class="bg-transparent text-right font-semibold">Nominal</th>
        <th class="w-20 bg-transparent text-right font-semibold"><span class="sr-only">Aksi</span></th>
      </tr>
    </thead>
    <tbody>
      {#each items as item (item.id)}
        <tr class="border-base-content/6 transition-colors hover:bg-base-200/60">
          <td>
            <div class="flex items-center gap-3">
              <span
                class="grid size-9 shrink-0 place-items-center rounded-xl text-xs font-bold text-white shadow-sm"
                style={`background-color: ${categoryColor(item.category)}`}
              >
                {categoryInitial(item.category)}
              </span>
              <div class="min-w-0">
                <p class="max-w-[12rem] truncate text-sm font-medium">{item.category}</p>
                <p class="max-w-[14rem] truncate text-[11px] text-base-content/45">
                  {item.note || (item.type === 'income' ? 'Pemasukan' : 'Pengeluaran')}
                </p>
              </div>
            </div>
          </td>
          {#if !compact}
            <td class="hidden md:table-cell">
              <span class="badge badge-ghost badge-sm max-w-[9rem] truncate">{item.wallet_name}</span>
            </td>
          {/if}
          <td class="hidden whitespace-nowrap text-xs text-base-content/50 sm:table-cell">
            {formatDate(item.occurred_at)}
          </td>
          <td class="whitespace-nowrap text-right">
            <span
              class="tabular text-sm font-semibold {item.type === 'income' ? 'text-success' : 'text-error'}"
            >
              {item.type === 'income' ? '+' : '−'}{formatMoney(item.amount_cents, currency)}
            </span>
          </td>
          <td>
            <div class="flex justify-end gap-0.5">
              <button
                type="button"
                class="btn btn-ghost btn-xs btn-circle text-base-content/40 hover:text-primary"
                title="Ubah transaksi"
                aria-label={`Ubah transaksi ${item.category}`}
                onclick={() => onedit(item)}
              >
                <Icon name="edit" size={14} />
              </button>
              {#if ondelete}
                <button
                  type="button"
                  class="btn btn-ghost btn-xs btn-circle text-base-content/40 hover:text-error"
                  title="Hapus transaksi"
                  aria-label={`Hapus transaksi ${item.category}`}
                  disabled={busyId === item.id}
                  onclick={() => ondelete?.(item)}
                >
                  {#if busyId === item.id}
                    <span class="loading loading-spinner loading-xs"></span>
                  {:else}
                    <Icon name="trash" size={14} />
                  {/if}
                </button>
              {/if}
            </div>
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>
