<script lang="ts">
  import type { Snippet } from 'svelte';
  import Icon from './Icon.svelte';

  let {
    icon = 'sparkles',
    title,
    description,
    children
  }: {
    icon?: 'wallet' | 'transactions' | 'sparkles' | 'alert';
    title: string;
    description: string;
    children?: Snippet;
  } = $props();
</script>

<div class="flex flex-col items-center justify-center px-6 py-12 text-center">
  <div class="grid size-14 place-items-center rounded-2xl bg-base-200 text-base-content/45">
    <Icon name={icon} size={26} />
  </div>
  <h3 class="mt-4 text-base font-semibold">{title}</h3>
  <p class="mt-1 max-w-sm text-sm leading-relaxed text-base-content/55">{description}</p>
  {#if children}
    <div class="mt-5">
      {@render children()}
    </div>
  {/if}
</div>
