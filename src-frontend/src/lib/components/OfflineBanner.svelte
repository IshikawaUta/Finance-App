<script lang="ts">
  import { loadSystemStatus, systemLoading, systemStatus } from '$lib/stores/system';
  import Icon from './Icon.svelte';

  const offline = $derived($systemStatus?.offline ?? false);
  const reason = $derived(
    $systemStatus?.last_error ??
      'Database belum terhubung. Periksa connection string dan whitelist IP Atlas Anda.'
  );
</script>

{#if offline}
  <div class="border-b border-warning/25 bg-warning/10 px-4 py-2.5 sm:px-6 lg:px-8">
    <div class="flex flex-wrap items-center gap-2 text-xs text-warning-content">
      <span class="grid size-6 place-items-center rounded-lg bg-warning/20 text-warning">
        <Icon name="alert" size={14} />
      </span>
      <span class="font-medium">Mode offline.</span>
      <span class="min-w-0 flex-1 truncate text-base-content/55" title={reason}>{reason}</span>
      <button
        type="button"
        class="btn btn-ghost btn-xs gap-1 text-base-content/60"
        disabled={$systemLoading}
        onclick={() => void loadSystemStatus()}
      >
        {#if $systemLoading}
          <span class="loading loading-spinner loading-xs"></span>
        {:else}
          <Icon name="refresh" size={13} />
        {/if}
        Coba lagi
      </button>
      <a href="/settings" class="btn btn-warning btn-xs">Pengaturan</a>
    </div>
  </div>
{/if}
