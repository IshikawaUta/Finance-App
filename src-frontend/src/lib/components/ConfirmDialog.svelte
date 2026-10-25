<script lang="ts">
  import Icon from './Icon.svelte';

  let {
    open = false,
    title = 'Konfirmasi',
    message = '',
    confirmLabel = 'Hapus',
    cancelLabel = 'Batal',
    danger = true,
    busy = false,
    onconfirm,
    oncancel
  }: {
    open?: boolean;
    title?: string;
    message?: string;
    confirmLabel?: string;
    cancelLabel?: string;
    danger?: boolean;
    busy?: boolean;
    onconfirm: () => void | Promise<void>;
    oncancel: () => void;
  } = $props();

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape' && open && !busy) oncancel();
  }

  // Render the overlay at body level so no page wrapper (transform, opacity,
  // stacking context) can keep it below the fixed sidebar.
  function portal(node: HTMLElement) {
    document.body.appendChild(node);
    return {
      destroy() {
        node.remove();
      }
    };
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
  <div use:portal class="fixed inset-0 z-[110] grid place-items-center p-4">
    <button
      type="button"
      class="absolute inset-0 bg-black/50 backdrop-blur-sm"
      aria-label="Tutup dialog"
      onclick={() => !busy && oncancel()}
    ></button>

    <div
      class="modal-panel surface relative max-h-[92vh] w-full max-w-md overflow-y-auto p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
    >
      <div class="flex items-start gap-4">
        <div
          class="grid size-11 shrink-0 place-items-center rounded-2xl {danger
            ? 'bg-error/12 text-error'
            : 'bg-primary/12 text-primary'}"
        >
          <Icon name={danger ? 'alert' : 'check'} size={20} />
        </div>
        <div>
          <h2 id="confirm-title" class="text-lg font-semibold">{title}</h2>
          <p class="mt-1 text-sm leading-relaxed text-base-content/60">{message}</p>
        </div>
      </div>
      <div class="mt-6 flex justify-end gap-2">
        <button type="button" class="btn btn-ghost" disabled={busy} onclick={oncancel}>
          {cancelLabel}
        </button>
        <button
          type="button"
          class="btn {danger ? 'btn-error' : 'btn-primary'}"
          disabled={busy}
          onclick={onconfirm}
        >
          {#if busy}
            <span class="loading loading-spinner loading-xs"></span>
          {/if}
          {confirmLabel}
        </button>
      </div>
    </div>
  </div>
{/if}
