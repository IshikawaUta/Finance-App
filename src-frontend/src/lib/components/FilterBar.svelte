<script lang="ts">
  import { onDestroy } from 'svelte';
  import type { TransactionFilters, TransactionType, Wallet } from '$lib/api/types';
  import Icon from './Icon.svelte';

  let {
    filters,
    wallets,
    categories,
    onchange,
    onreset
  }: {
    filters: TransactionFilters;
    wallets: Wallet[];
    categories: string[];
    onchange: (patch: Partial<TransactionFilters>) => void;
    onreset: () => void;
  } = $props();

  let search = $state('');
  let searchFocused = $state(false);
  let debounce: ReturnType<typeof setTimeout> | null = null;

  $effect(() => {
    if (!searchFocused && filters.search !== search) {
      search = filters.search;
    }
  });

  onDestroy(() => {
    if (debounce) clearTimeout(debounce);
  });

  function handleSearch(event: Event) {
    search = (event.currentTarget as HTMLInputElement).value;
    if (debounce) clearTimeout(debounce);
    debounce = setTimeout(() => {
      onchange({ search, page: 1 });
    }, 320);
  }

  function handleType(event: Event) {
    const value = (event.currentTarget as HTMLSelectElement).value;
    onchange({ types: value ? ([value] as TransactionType[]) : [], page: 1 });
  }

  function handleWallet(event: Event) {
    const value = (event.currentTarget as HTMLSelectElement).value;
    onchange({ wallet_ids: value ? [value] : [], page: 1 });
  }

  function handleCategory(event: Event) {
    const value = (event.currentTarget as HTMLSelectElement).value;
    onchange({ categories: value ? [value] : [], page: 1 });
  }

  function handleDateFrom(event: Event) {
    const value = (event.currentTarget as HTMLInputElement).value;
    onchange({ date_from: value || null, page: 1 });
  }

  function handleDateTo(event: Event) {
    const value = (event.currentTarget as HTMLInputElement).value;
    onchange({ date_to: value || null, page: 1 });
  }

  function handleSort(event: Event) {
    const value = (event.currentTarget as HTMLSelectElement).value;
    if (value === 'oldest') {
      onchange({ sort_by: 'occurred_at', sort_dir: 'asc', page: 1 });
    } else if (value === 'largest') {
      onchange({ sort_by: 'amount_cents', sort_dir: 'desc', page: 1 });
    } else if (value === 'smallest') {
      onchange({ sort_by: 'amount_cents', sort_dir: 'asc', page: 1 });
    } else {
      onchange({ sort_by: 'occurred_at', sort_dir: 'desc', page: 1 });
    }
  }

  const sortValue = $derived(
    filters.sort_by === 'amount_cents'
      ? filters.sort_dir === 'asc'
        ? 'smallest'
        : 'largest'
      : filters.sort_dir === 'asc'
        ? 'oldest'
        : 'newest'
  );
</script>

<div class="surface p-4">
  <div class="grid gap-3 lg:grid-cols-12">
    <label class="input input-bordered flex items-center gap-2 lg:col-span-4">
      <Icon name="search" size={16} class="text-base-content/40" />
      <input
        id="filter-search"
        type="search"
        class="grow border-0 bg-transparent text-sm outline-none"
        placeholder="Cari catatan atau kategori…"
        value={search}
        oninput={handleSearch}
        onfocus={() => (searchFocused = true)}
        onblur={() => (searchFocused = false)}
      />
    </label>

    <select class="select select-bordered text-sm lg:col-span-2" aria-label="Tipe transaksi" onchange={handleType}>
      <option value="" selected={filters.types.length === 0}>Semua tipe</option>
      <option value="income" selected={filters.types.includes('income')}>Pemasukan</option>
      <option value="expense" selected={filters.types.includes('expense')}>Pengeluaran</option>
    </select>

    <select class="select select-bordered text-sm lg:col-span-2" aria-label="Dompet" onchange={handleWallet}>
      <option value="" selected={filters.wallet_ids.length === 0}>Semua dompet</option>
      {#each wallets as wallet (wallet.id)}
        <option value={wallet.id} selected={filters.wallet_ids.includes(wallet.id)}>{wallet.name}</option>
      {/each}
    </select>

    <select class="select select-bordered text-sm lg:col-span-2" aria-label="Kategori" onchange={handleCategory}>
      <option value="" selected={filters.categories.length === 0}>Semua kategori</option>
      {#each categories as category (category)}
        <option value={category} selected={filters.categories.includes(category)}>{category}</option>
      {/each}
    </select>

    <select class="select select-bordered text-sm lg:col-span-2" aria-label="Urutkan" onchange={handleSort}>
      <option value="newest" selected={sortValue === 'newest'}>Terbaru</option>
      <option value="oldest" selected={sortValue === 'oldest'}>Terlama</option>
      <option value="largest" selected={sortValue === 'largest'}>Nominal terbesar</option>
      <option value="smallest" selected={sortValue === 'smallest'}>Nominal terkecil</option>
    </select>

    <label class="input input-bordered flex items-center gap-2 lg:col-span-3">
      <Icon name="calendar" size={15} class="text-base-content/40" />
      <input
        type="date"
        class="grow border-0 bg-transparent text-xs outline-none"
        aria-label="Tanggal awal"
        value={filters.date_from ?? ''}
        onchange={handleDateFrom}
      />
    </label>

    <span class="hidden items-center justify-center text-xs text-base-content/35 lg:col-span-1 lg:flex">s/d</span>

    <label class="input input-bordered flex items-center gap-2 lg:col-span-3">
      <Icon name="calendar" size={15} class="text-base-content/40" />
      <input
        type="date"
        class="grow border-0 bg-transparent text-xs outline-none"
        aria-label="Tanggal akhir"
        value={filters.date_to ?? ''}
        onchange={handleDateTo}
      />
    </label>

    <button type="button" class="btn btn-ghost text-sm lg:col-span-2" onclick={onreset}>
      <Icon name="refresh" size={15} />
      Reset filter
    </button>
  </div>
</div>
