<script lang="ts">
  import Icon from './Icon.svelte';
  import { formatPercent } from '$lib/utils/format';

  let {
    title,
    value,
    icon = 'wallet',
    tone = 'primary',
    trend = null,
    invertTrend = false,
    caption = '',
    loading = false
  }: {
    title: string;
    value: string;
    icon?: 'wallet' | 'arrow-up' | 'arrow-down' | 'chart';
    tone?: 'primary' | 'success' | 'error' | 'secondary';
    trend?: number | null;
    invertTrend?: boolean;
    caption?: string;
    loading?: boolean;
  } = $props();

  const tones: Record<string, { badge: string; icon: string }> = {
    primary: { badge: 'bg-primary/12 text-primary', icon: 'bg-primary/12 text-primary' },
    success: { badge: 'bg-success/12 text-success', icon: 'bg-success/12 text-success' },
    error: { badge: 'bg-error/12 text-error', icon: 'bg-error/12 text-error' },
    secondary: { badge: 'bg-secondary/12 text-secondary', icon: 'bg-secondary/12 text-secondary' }
  };
</script>

<article class="surface surface-hover p-5">
  <div class="flex items-start justify-between gap-3">
    <div class="min-w-0">
      <p class="text-xs font-medium uppercase tracking-wider text-base-content/55">{title}</p>
      {#if loading}
        <div class="skeleton mt-3 h-8 w-36 rounded-lg"></div>
        <div class="skeleton mt-2 h-3 w-24 rounded"></div>
      {:else}
        <p class="tabular mt-2 truncate text-2xl font-semibold tracking-tight">{value}</p>
        <div class="mt-2 flex min-h-5 items-center gap-2">
          {#if trend !== null && trend !== undefined}
            <span
              class="badge badge-sm border-0 {(trend >= 0) !== invertTrend
                ? 'bg-success/12 text-success'
                : 'bg-error/12 text-error'}"
            >
              <Icon name={trend >= 0 ? 'arrow-up' : 'arrow-down'} size={11} />
              {formatPercent(trend)}
            </span>
          {/if}
          {#if caption}
            <span class="truncate text-xs text-base-content/50">{caption}</span>
          {/if}
        </div>
      {/if}
    </div>
    <div class="grid size-11 shrink-0 place-items-center rounded-2xl {tones[tone].icon}">
      <Icon name={icon} size={20} />
    </div>
  </div>
</article>
