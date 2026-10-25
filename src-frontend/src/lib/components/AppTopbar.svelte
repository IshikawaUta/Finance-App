<script lang="ts">
  import { page } from '$app/stores';
  import { currentUser } from '$lib/stores/auth';
  import { systemStatus } from '$lib/stores/system';
  import { openTransactionModal, theme, toggleTheme } from '$lib/stores/ui';
  import { initials } from '$lib/utils/format';
  import Icon from './Icon.svelte';

  let { onmenu }: { onmenu: () => void } = $props();

  const meta: Record<string, { title: string; subtitle: string }> = {
    '/dashboard': { title: 'Dashboard', subtitle: 'Ringkasan keuangan Anda hari ini' },
    '/wallets': { title: 'Dompet', subtitle: 'Kelola semua sumber dana Anda' },
    '/transactions': { title: 'Transaksi', subtitle: 'Riwayat pemasukan dan pengeluaran' },
    '/settings': { title: 'Pengaturan', subtitle: 'Akun, tampilan, dan koneksi database' }
  };

  const current = $derived(
    meta[$page.url.pathname] ?? { title: 'FinanceApp', subtitle: 'Keuangan pribadi, rapi.' }
  );

  const online = $derived($systemStatus?.db_connected ?? true);
</script>

<header
  class="sticky top-0 z-30 border-b border-base-content/8 bg-base-200"
>
  <div class="flex h-16 items-center gap-3 px-4 sm:px-6 lg:px-8">
    <button
      type="button"
      class="menu-toggle grid size-8 shrink-0 place-items-center rounded-xl border-0 bg-transparent p-0 lg:hidden"
      aria-label="Buka menu"
      onclick={onmenu}
    >
      <Icon name="menu" size={20} />
    </button>

    <div class="min-w-0 flex-1">
      <h1 class="truncate text-base font-semibold tracking-tight sm:text-lg">{current.title}</h1>
      <p class="hidden truncate text-xs text-base-content/45 sm:block">{current.subtitle}</p>
    </div>

    <div
      class="hidden items-center gap-1.5 rounded-full border border-base-content/8 bg-base-100/70 px-3 py-1.5 text-[11px] font-medium text-base-content/55 md:flex"
      title={online ? 'Terhubung ke database' : 'Database tidak terhubung'}
    >
      <span class="live-dot size-1.5 rounded-full {online ? 'bg-success' : 'bg-error'}"></span>
      {online ? 'Online' : 'Offline'}
    </div>

    <button
      type="button"
      class="btn btn-ghost btn-sm btn-circle"
      aria-label={$theme === 'dark' ? 'Aktifkan mode terang' : 'Aktifkan mode gelap'}
      title={$theme === 'dark' ? 'Mode terang' : 'Mode gelap'}
      onclick={toggleTheme}
    >
      <Icon name={$theme === 'dark' ? 'sun' : 'moon'} size={19} />
    </button>

    <button
      type="button"
      class="btn btn-primary btn-sm hidden gap-1.5 sm:inline-flex"
      onclick={() => openTransactionModal({ defaultType: 'expense' })}
    >
      <Icon name="plus" size={16} />
      <span class="hidden md:inline">Transaksi</span>
    </button>

    <div
      class="grid size-9 place-items-center rounded-full border border-base-content/8 bg-base-100 text-xs font-bold text-primary"
      title={$currentUser?.name ?? 'Pengguna'}
    >
      {initials($currentUser?.name ?? 'Pengguna')}
    </div>
  </div>
</header>
