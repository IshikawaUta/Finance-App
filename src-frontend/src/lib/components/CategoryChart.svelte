<script lang="ts">
  import { Chart, type ChartConfiguration } from 'chart.js';
  import type { CategorySlice } from '$lib/api/types';
  import { CHART_COLORS } from '$lib/charts';
  import { theme } from '$lib/stores/ui';
  import { formatMoney } from '$lib/utils/format';

  let {
    slices,
    currency = 'IDR',
    loading = false
  }: {
    slices: CategorySlice[];
    currency?: string;
    loading?: boolean;
  } = $props();

  let canvas = $state<HTMLCanvasElement | null>(null);
  let chart: Chart<'doughnut'> | null = null;

  const total = $derived(slices.reduce((sum, slice) => sum + slice.amount_cents, 0));
  const topSlices = $derived(slices.slice(0, 6));

  $effect(() => {
    const element = canvas;
    const data = slices;
    const currentCurrency = currency;
    const dark = $theme === 'dark';

    if (!element) return;

    chart?.destroy();
    chart = null;

    const config: ChartConfiguration<'doughnut'> = {
      type: 'doughnut',
      data: {
        labels: data.map((slice) => slice.category),
        datasets: [
          {
            data: data.map((slice) => slice.amount_cents),
            backgroundColor: data.map((_, index) => CHART_COLORS[index % CHART_COLORS.length]),
            borderColor: dark ? '#111827' : '#ffffff',
            borderWidth: 3,
            hoverOffset: 5
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '72%',
        animation: { duration: 500 },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: dark ? 'rgba(15, 23, 42, 0.96)' : 'rgba(15, 23, 42, 0.92)',
            titleColor: '#f8fafc',
            bodyColor: '#e2e8f0',
            padding: 10,
            cornerRadius: 10,
            callbacks: {
              label: (item) =>
                ` ${formatMoney(Number(item.raw), currentCurrency)} (${data[item.dataIndex]?.percentage ?? 0}%)`
            }
          }
        }
      }
    };

    chart = new Chart(element, config);

    return () => {
      chart?.destroy();
      chart = null;
    };
  });
</script>

{#if loading}
  <div class="flex flex-col items-center gap-4">
    <div class="skeleton size-[200px] rounded-full"></div>
    <div class="skeleton h-4 w-40 rounded"></div>
  </div>
{:else if slices.length === 0}
  <div class="flex h-[260px] flex-col items-center justify-center text-center">
    <div class="grid size-12 place-items-center rounded-2xl bg-base-200 text-base-content/35">
      <span class="text-lg">◎</span>
    </div>
    <p class="mt-3 text-sm font-medium text-base-content/60">Belum ada pengeluaran</p>
    <p class="mt-1 max-w-[15rem] text-xs text-base-content/40">
      Grafik kategori akan muncul setelah Anda mencatat pengeluaran.
    </p>
  </div>
{:else}
  <div class="flex flex-col items-center gap-5">
    <div class="relative size-[200px]">
      <canvas bind:this={canvas} aria-label="Grafik pengeluaran per kategori"></canvas>
      <div class="pointer-events-none absolute inset-0 grid place-items-center text-center">
        <div>
          <p class="text-[10px] font-medium uppercase tracking-wider text-base-content/40">Total</p>
          <p class="tabular mt-0.5 text-sm font-semibold">
            {formatMoney(total, currency, { compact: true })}
          </p>
        </div>
      </div>
    </div>

    <ul class="w-full space-y-2">
      {#each topSlices as slice, index (slice.category)}
        <li class="flex items-center gap-2.5 text-xs">
          <span
            class="size-2.5 shrink-0 rounded-full"
            style={`background-color: ${CHART_COLORS[index % CHART_COLORS.length]}`}
          ></span>
          <span class="min-w-0 flex-1 truncate text-base-content/65">{slice.category}</span>
          <span class="tabular font-medium text-base-content/80">
            {formatMoney(slice.amount_cents, currency, { compact: true })}
          </span>
          <span class="tabular w-10 text-right text-base-content/40">{slice.percentage}%</span>
        </li>
      {/each}
    </ul>
  </div>
{/if}
