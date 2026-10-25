<script lang="ts">
  import { toasts, dismissToast } from '$lib/stores/ui';
  import Icon from './Icon.svelte';

  const styles: Record<string, string> = {
    success: 'alert-success',
    error: 'alert-error',
    info: 'alert-info'
  };
  const icons: Record<string, 'check' | 'alert' | 'sparkles'> = {
    success: 'check',
    error: 'alert',
    info: 'sparkles'
  };
</script>

<div class="toast toast-top toast-end pointer-events-none z-[120] w-full max-w-sm gap-2 p-4">
  {#each $toasts as toast (toast.id)}
    <div class="alert {styles[toast.kind]} toast-item pointer-events-auto shadow-lg" role="status">
      <Icon name={icons[toast.kind]} size={18} />
      <span class="text-sm font-medium">{toast.message}</span>
      <button
        type="button"
        class="btn btn-ghost btn-xs btn-circle"
        aria-label="Tutup notifikasi"
        onclick={() => dismissToast(toast.id)}
      >
        <Icon name="close" size={14} />
      </button>
    </div>
  {/each}
</div>
