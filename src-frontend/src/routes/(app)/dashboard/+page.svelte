<script lang="ts">
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { api } from '$lib/api/commands';
  import type { PeriodKey } from '$lib/api/types';
  import CashflowChart from '$lib/components/CashflowChart.svelte';
  import CategoryChart from '$lib/components/CategoryChart.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import Icon from '$lib/components/Icon.svelte';
  import StatCard from '$lib/components/StatCard.svelte';
  import TransactionTable from '$lib/components/TransactionTable.svelte';
  import { authToken, currentUser } from '$lib/stores/auth';
  import {
    dashboard,
    dashboardCustomRange,
    dashboardError,
    dashboardLoading,
    dashboardPeriod,
    dashboardWalletIds,
    loadDashboard,
    setDashboardPeriod
  } from '$lib/stores/dashboard';
  import {
    bumpData,
    onDataChange,
    openTransactionModal,
    openWalletModal,
    pushToast
  } from '$lib/stores/ui';
  import { loadWallets, wallets, walletsLoading } from '$lib/stores/wallets';
  import { formatDateLong, formatMoney, todayInputValue } from '$lib/utils/format';
  import { PERIOD_OPTIONS, periodLabel, rangeLabel } from '$lib/utils/periods';

  let customFrom = $state('');
  let customTo = $state('');
  let seeding = $state(false);

  const summary = $derived($dashboard?.summary ?? null);
  const cashflow = $derived($dashboard?.cashflow ?? []);
  const categories = $derived($dashboard?.expense_by_category ?? []);
  const recent = $derived($dashboard?.recent_transactions ?? []);
  const periodInfo = $derived($dashboard?.period ?? null);
  const currency = $derived($currentUser?.base_currency ?? 'IDR');
  const isLoading = $derived($dashboardLoading && !$dashboard);
  const showEmpty = $derived(!$walletsLoading && $wallets.length === 0);
  const selectedWallet = $derived($dashboardWalletIds[0] ?? '');

  const greeting = $derived(
    (() => {
      const hour = new Date().getHours();
      if (hour < 11) return 'Selamat pagi';
      if (hour < 15) return 'Selamat siang';
      if (hour < 19) return 'Selamat sore';
      return 'Selamat malam';
    })()
  );

  const firstName = $derived(($currentUser?.name ?? 'Pengguna').split(' ')[0]);

  onMount(() => {
    void loadWallets();
    void loadDashboard();
    return onDataChange(() => {
      void loadDashboard();
      void loadWallets(true);
    });
  });

  function handlePeriod(event: Event) {
    const value = (event.currentTarget as HTMLSelectElement).value as PeriodKey;
    if (value === 'custom') {
      if (!customFrom) customFrom = $dashboardCustomRange.from || todayInputValue();
      if (!customTo) customTo = $dashboardCustomRange.to || todayInputValue();
    }
    void setDashboardPeriod(value);
  }

  function applyCustomRange() {
    if (!customFrom || !customTo) {
      pushToast('Pilih tanggal awal dan akhir terlebih dahulu.', 'error');
      return;
    }
    dashboardCustomRange.set({ from: customFrom, to: customTo });
    void loadDashboard({ period: 'custom' });
  }

  function handleWallet(event: Event) {
    const value = (event.currentTarget as HTMLSelectElement).value;
    dashboardWalletIds.set(value ? [value] : []);
    void loadDashboard();
  }

  async function seedDemo() {
    const token = get(authToken);
    if (!token || seeding) return;
    seeding = true;
    try {
      const response = await api.seedDemo(token);
      pushToast(response.message, response.message.includes('dibuat') ? 'success' : 'info');
      bumpData();
      await Promise.all([loadWallets(true), loadDashboard()]);
    } catch (caught) {
      pushToast(caught instanceof Error ? caught.message : 'Gagal membuat data contoh.', 'error');
    } finally {
      seeding = false;
    }
  }
</script>

<div class="space-y-5">
  <header class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-primary">{greeting}</p>
      <h2 class="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">Halo, {firstName}</h2>
      <p class="mt-1 text-sm capitalize text-base-content/45">{formatDateLong()}</p>
    </div>

    <div class="flex flex-wrap items-center gap-2">
      <select
        class="select select-bordered select-sm text-xs"
        aria-label="Pilih periode"
        value={$dashboardPeriod}
        onchange={handlePeriod}
      >
        {#each PERIOD_OPTIONS as option (option.value)}
          <option value={option.value}>{option.label}</option>
        {/each}
      </select>

      <select
        class="select select-bordered select-sm max-w-40 text-xs"
        aria-label="Filter dompet"
        value={selectedWallet}
        onchange={handleWallet}
      >
        <option value="">Semua dompet</option>
        {#each $wallets as wallet (wallet.id)}
          <option value={wallet.id}>{wallet.name}</option>
        {/each}
      </select>

      {#if $dashboardPeriod === 'custom'}
        <input
          type="date"
          class="input input-bordered input-sm w-36 text-xs"
          aria-label="Tanggal awal"
          bind:value={customFrom}
        />
        <span class="text-xs text-base-content/35">s/d</span>
        <input
          type="date"
          class="input input-bordered input-sm w-36 text-xs"
          aria-label="Tanggal akhir"
          bind:value={customTo}
        />
        <button type="button" class="btn btn-primary btn-sm" onclick={applyCustomRange}>Terapkan</button>
      {/if}
    </div>
  </header>

  {#if $dashboardError}
    <div class="alert alert-error text-sm" role="alert">
      <Icon name="alert" size={17} />
      <span>{$dashboardError}</span>
      <button type="button" class="btn btn-ghost btn-xs" onclick={() => void loadDashboard()}>
        Coba lagi
      </button>
    </div>
  {/if}

  {#if showEmpty}
    <div class="surface">
      <EmptyState
        icon="wallet"
        title="Belum ada dompet"
        description="Tambahkan dompet pertama Anda, lalu mulai catat pemasukan dan pengeluaran. Atau muat data contoh untuk melihat cara kerja FinanceApp."
      >
        <div class="flex flex-wrap justify-center gap-2">
          <button type="button" class="btn btn-primary" onclick={() => openWalletModal()}>
            <Icon name="plus" size={16} />
            Buat dompet pertama
          </button>
          <button type="button" class="btn btn-ghost" disabled={seeding} onclick={seedDemo}>
            {#if seeding}
              <span class="loading loading-spinner loading-xs"></span>
            {:else}
              <Icon name="sparkles" size={16} />
            {/if}
            Muat data contoh
          </button>
        </div>
      </EmptyState>
    </div>
  {:else}
    <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard
        title="Total saldo"
        value={summary ? formatMoney(summary.total_balance_cents, currency) : '—'}
        icon="wallet"
        tone="primary"
        caption={`${summary?.wallet_count ?? 0} dompet aktif`}
        loading={isLoading}
      />
      <StatCard
        title="Pemasukan"
        value={summary ? formatMoney(summary.period_income_cents, currency) : '—'}
        icon="arrow-up"
        tone="success"
        trend={summary?.income_change_pct ?? null}
        caption="vs periode sebelumnya"
        loading={isLoading}
      />
      <StatCard
        title="Pengeluaran"
        value={summary ? formatMoney(summary.period_expense_cents, currency) : '—'}
        icon="arrow-down"
        tone="error"
        trend={summary?.expense_change_pct ?? null}
        invertTrend
        caption="vs periode sebelumnya"
        loading={isLoading}
      />
      <StatCard
        title="Arus kas bersih"
        value={summary ? formatMoney(summary.period_net_cents, currency, { signed: true }) : '—'}
        icon="chart"
        tone={(summary?.period_net_cents ?? 0) >= 0 ? 'success' : 'error'}
        caption={`${summary?.transaction_count ?? 0} transaksi`}
        loading={isLoading}
      />
    </div>

    <div class="grid gap-4 xl:grid-cols-3">
      <section class="surface p-5 xl:col-span-2">
        <div class="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h3 class="text-sm font-semibold">Arus kas</h3>
            <p class="mt-0.5 text-xs text-base-content/45">
              {periodInfo
                ? rangeLabel(periodInfo.start, periodInfo.end)
                : periodLabel($dashboardPeriod)}
            </p>
          </div>
          <span class="badge badge-ghost badge-sm">{periodLabel($dashboardPeriod)}</span>
        </div>
        <div class="mt-4">
          <CashflowChart
            points={cashflow}
            granularity={periodInfo?.granularity ?? 'day'}
            {currency}
            loading={isLoading}
          />
        </div>
      </section>

      <section class="surface p-5">
        <div>
          <h3 class="text-sm font-semibold">Pengeluaran per kategori</h3>
          <p class="mt-0.5 text-xs text-base-content/45">
            {periodInfo
              ? rangeLabel(periodInfo.start, periodInfo.end)
              : 'Distribusi pengeluaran'}
          </p>
        </div>
        <div class="mt-5">
          <CategoryChart slices={categories} {currency} loading={isLoading} />
        </div>
      </section>
    </div>

    {#if $wallets.length > 0}
      <section>
        <div class="mb-2.5 flex items-center justify-between">
          <h3 class="text-sm font-semibold">Dompet Anda</h3>
          <a href="/wallets" class="text-xs font-medium text-primary hover:underline">Kelola dompet</a>
        </div>
        <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {#each $wallets.slice(0, 4) as wallet (wallet.id)}
            <a
              href="/wallets"
              class="surface surface-hover flex items-center gap-3 p-4"
            >
              <span
                class="grid size-9 shrink-0 place-items-center rounded-xl text-white"
                style={`background-color: ${wallet.color}`}
              >
                <Icon name="wallet" size={16} />
              </span>
              <div class="min-w-0 flex-1">
                <p class="truncate text-xs font-medium text-base-content/55">{wallet.name}</p>
                <p class="tabular mt-0.5 truncate text-sm font-semibold">
                  {formatMoney(wallet.balance_cents, wallet.currency)}
                </p>
              </div>
              <Icon name="chevron-right" size={14} class="text-base-content/25" />
            </a>
          {/each}
        </div>
      </section>
    {/if}

    <section class="surface p-5">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-sm font-semibold">Transaksi terakhir</h3>
          <p class="mt-0.5 text-xs text-base-content/45">Aktivitas terbaru dari semua dompet</p>
        </div>
        <a href="/transactions" class="text-xs font-medium text-primary hover:underline">
          Lihat semua
        </a>
      </div>

      <div class="mt-4">
        {#if isLoading}
          <div class="space-y-3">
            {#each Array(4) as _, index (index)}
              <div class="flex items-center gap-3">
                <div class="skeleton size-9 rounded-xl"></div>
                <div class="flex-1 space-y-2">
                  <div class="skeleton h-3 w-32 rounded"></div>
                  <div class="skeleton h-2.5 w-20 rounded"></div>
                </div>
                <div class="skeleton h-3 w-24 rounded"></div>
              </div>
            {/each}
          </div>
        {:else if recent.length > 0}
          <TransactionTable
            items={recent}
            {currency}
            compact
            onedit={(transaction) => openTransactionModal({ transaction })}
          />
        {:else}
          <EmptyState
            icon="transactions"
            title="Belum ada transaksi"
            description="Catat pengeluaran atau pemasukan pertama Anda untuk melihat ringkasan di sini."
          >
            <button
              type="button"
              class="btn btn-primary btn-sm"
              onclick={() => openTransactionModal({ defaultType: 'expense' })}
            >
              <Icon name="plus" size={15} />
              Tambah transaksi
            </button>
          </EmptyState>
        {/if}
      </div>
    </section>
  {/if}
</div>
