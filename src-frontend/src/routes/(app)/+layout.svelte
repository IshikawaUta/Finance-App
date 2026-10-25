<script lang="ts">
  import { onMount, type Snippet } from 'svelte';
  import { goto } from '$app/navigation';
  import AppSidebar from '$lib/components/AppSidebar.svelte';
  import AppTopbar from '$lib/components/AppTopbar.svelte';
  import OfflineBanner from '$lib/components/OfflineBanner.svelte';
  import TransactionModal from '$lib/components/TransactionModal.svelte';
  import WalletModal from '$lib/components/WalletModal.svelte';
  import Icon from '$lib/components/Icon.svelte';
  import { authReady, clearSession, isAuthenticated } from '$lib/stores/auth';
  import { resetDashboard } from '$lib/stores/dashboard';
  import { resetTransactions } from '$lib/stores/transactions';
  import { startSystemPolling } from '$lib/stores/system';
  import { loadWallets, resetWallets, walletsLoaded } from '$lib/stores/wallets';

  let { children }: { children: Snippet } = $props();
  let sidebarOpen = $state(false);

  onMount(() => {
    const stopPolling = startSystemPolling();
    const onUnauthorized = () => {
      clearSession();
      void goto('/login', { replaceState: true });
    };
    window.addEventListener('finance:unauthorized', onUnauthorized);
    return () => {
      stopPolling();
      window.removeEventListener('finance:unauthorized', onUnauthorized);
    };
  });

  $effect(() => {
    if ($authReady && !$isAuthenticated) {
      resetWallets();
      resetDashboard();
      resetTransactions();
      void goto('/login', { replaceState: true });
    }
  });

  $effect(() => {
    if ($authReady && $isAuthenticated && !$walletsLoaded) {
      void loadWallets(true);
    }
  });
</script>

{#if !$authReady}
  <div class="grid min-h-screen place-items-center px-6">
    <div class="flex flex-col items-center gap-4 text-center">
      <span
        class="grid size-14 place-items-center rounded-2xl bg-gradient-to-br from-primary to-secondary text-primary-content shadow-xl shadow-primary/20"
      >
        <Icon name="chart" size={26} strokeWidth={2.2} />
      </span>
      <p class="text-sm text-base-content/45">Memuat sesi Anda…</p>
      <span class="loading loading-spinner loading-sm text-primary"></span>
    </div>
  </div>
{:else if $isAuthenticated}
  <div class="min-h-screen lg:pl-[272px]">
    <AppSidebar open={sidebarOpen} onclose={() => (sidebarOpen = false)} />

    <div class="flex min-h-screen flex-col">
      <AppTopbar onmenu={() => (sidebarOpen = true)} />
      <OfflineBanner />

      <main class="flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <div class="page-enter mx-auto w-full max-w-7xl">
          {@render children()}
        </div>
      </main>
    </div>
  </div>

  <TransactionModal />
  <WalletModal />
{:else}
  <div class="grid min-h-screen place-items-center px-6">
    <div class="flex flex-col items-center gap-3 text-center">
      <span class="loading loading-spinner loading-md text-primary"></span>
      <p class="text-sm text-base-content/45">Mengalihkan ke halaman masuk…</p>
    </div>
  </div>
{/if}
