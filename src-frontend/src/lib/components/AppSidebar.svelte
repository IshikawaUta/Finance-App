<script lang="ts">
  import { page } from '$app/stores';
  import { currentUser, logout } from '$lib/stores/auth';
  import { openTransactionModal } from '$lib/stores/ui';
  import { initials } from '$lib/utils/format';
  import Icon from './Icon.svelte';

  let { open = false, onclose }: { open?: boolean; onclose: () => void } = $props();

  const navigation = [
    { href: '/dashboard', label: 'Dashboard', icon: 'dashboard' as const },
    { href: '/wallets', label: 'Dompet', icon: 'wallet' as const },
    { href: '/transactions', label: 'Transaksi', icon: 'transactions' as const },
    { href: '/settings', label: 'Pengaturan', icon: 'settings' as const }
  ];

  function isActive(href: string): boolean {
    const path = $page.url.pathname;
    return path === href || path.startsWith(`${href}/`);
  }

  async function handleLogout() {
    onclose();
    await logout();
  }
</script>

{#if open}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-black/45 lg:hidden"
    aria-label="Tutup menu"
    onclick={onclose}
  ></button>
{/if}

<aside
  class="sidebar-panel fixed inset-y-0 left-0 z-50 flex w-[272px] flex-col border-r border-base-content/8 bg-base-100"
  class:sidebar-open={open}
>
  <div class="flex items-center justify-between px-5 pb-5 pt-6">
    <a href="/dashboard" class="flex items-center gap-3" onclick={onclose}>
      <span
        class="grid size-10 place-items-center rounded-2xl bg-gradient-to-br from-primary to-secondary text-primary-content shadow-lg shadow-primary/20"
      >
        <Icon name="chart" size={20} strokeWidth={2.2} />
      </span>
      <span>
        <span class="block text-[15px] font-semibold leading-tight tracking-tight">FinanceApp</span>
        <span class="block text-[11px] font-medium uppercase tracking-[0.14em] text-base-content/40"
          >Personal money</span
        >
      </span>
    </a>
    <button
      type="button"
      class="btn btn-ghost btn-sm btn-circle lg:hidden"
      aria-label="Tutup menu"
      onclick={onclose}
    >
      <Icon name="close" size={18} />
    </button>
  </div>

  <div class="px-4">
    <button
      type="button"
      class="btn btn-primary w-full justify-start gap-2 shadow-lg shadow-primary/20"
      onclick={() => {
        openTransactionModal({ defaultType: 'expense' });
        onclose();
      }}
    >
      <Icon name="plus" size={18} />
      Tambah transaksi
    </button>
  </div>

  <nav class="mt-6 flex-1 space-y-1 overflow-y-auto px-3" aria-label="Navigasi utama">
    <p class="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-base-content/35">
      Menu
    </p>
    {#each navigation as item (item.href)}
      <a
        href={item.href}
        onclick={onclose}
        aria-current={isActive(item.href) ? 'page' : undefined}
        class="group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors {isActive(
          item.href
        )
          ? 'bg-primary/10 text-primary'
          : 'text-base-content/65 hover:bg-base-200 hover:text-base-content'}"
      >
        <span
          class="grid size-8 place-items-center rounded-lg transition-colors {isActive(item.href)
            ? 'bg-primary/12 text-primary'
            : 'bg-base-200 text-base-content/45 group-hover:text-base-content/70'}"
        >
          <Icon name={item.icon} size={17} />
        </span>
        {item.label}
        {#if isActive(item.href)}
          <span class="ml-auto size-1.5 rounded-full bg-primary"></span>
        {/if}
      </a>
    {/each}
  </nav>

  <div class="border-t border-base-content/8 p-3">
    <div class="flex items-center gap-3 rounded-xl px-2 py-2">
      <div
        class="grid size-9 shrink-0 place-items-center rounded-full bg-gradient-to-br from-primary/20 to-secondary/20 text-xs font-bold text-primary"
      >
        {initials($currentUser?.name ?? 'Pengguna')}
      </div>
      <div class="min-w-0 flex-1">
        <p class="truncate text-sm font-semibold">{$currentUser?.name ?? 'Pengguna'}</p>
        <p class="truncate text-[11px] text-base-content/45">{$currentUser?.email ?? ''}</p>
      </div>
      <button
        type="button"
        class="btn btn-ghost btn-xs btn-circle text-base-content/45 hover:text-error"
        title="Keluar"
        aria-label="Keluar dari akun"
        onclick={handleLogout}
      >
        <Icon name="logout" size={16} />
      </button>
    </div>
  </div>
</aside>
