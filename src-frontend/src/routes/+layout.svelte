<script lang="ts">
  import { onMount, type Snippet } from 'svelte';
  import '../app.css';
  import ToastHost from '$lib/components/ToastHost.svelte';
  import { bootstrapAuth } from '$lib/stores/auth';
  import { initTheme } from '$lib/stores/ui';

  let { children }: { children: Snippet } = $props();

  onMount(() => {
    initTheme();
    void bootstrapAuth();
  });
</script>

{@render children()}
<ToastHost />
