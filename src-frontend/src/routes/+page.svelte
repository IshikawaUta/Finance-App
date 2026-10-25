<script lang="ts">
  import { goto } from '$app/navigation';
  import { authReady, isAuthenticated } from '$lib/stores/auth';
  import Icon from '$lib/components/Icon.svelte';

  $effect(() => {
    if ($authReady) {
      void goto($isAuthenticated ? '/dashboard' : '/login', { replaceState: true });
    }
  });
</script>

<div class="grid min-h-screen place-items-center px-6">
  <div class="flex flex-col items-center gap-4 text-center">
    <span
      class="grid size-14 place-items-center rounded-2xl bg-gradient-to-br from-primary to-secondary text-primary-content shadow-xl shadow-primary/20"
    >
      <Icon name="chart" size={26} strokeWidth={2.2} />
    </span>
    <div>
      <p class="text-lg font-semibold tracking-tight">FinanceApp</p>
      <p class="mt-1 text-sm text-base-content/45">Menyiapkan ruang keuangan Anda…</p>
    </div>
    <span class="loading loading-spinner loading-sm text-primary"></span>
  </div>
</div>
