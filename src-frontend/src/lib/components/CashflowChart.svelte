<script lang="ts">
  import { Chart, type ChartConfiguration } from 'chart.js';
  import type { CashflowPoint } from '$lib/api/types';
  import { theme } from '$lib/stores/ui';
  import { formatMoney } from '$lib/utils/format';
  import { cashflowLabel } from '$lib/utils/periods';
  import '$lib/charts';

  let {
    points,
    granularity = 'day',
    currency = 'IDR',
    loading = false
  }: {
    points: CashflowPoint[];
    granularity?: 'day' | 'week' | 'month';
    currency?: string;
    loading?: boolean;
  } = $props();

  let canvas = $state<HTMLCanvasElement | null>(null);
  let chart: Chart<'line'> | null = null;

  const total = $derived(points.reduce((sum, point) => sum + point.income_cents + point.expense_cents, 0));

  $effect(() => {
    const element = canvas;
    const series = points;
    const unit = granularity;
    const currentCurrency = currency;
    const dark = $theme === 'dark';

    if (!element) return;

    chart?.destroy();
    chart = null;

    const context = element.getContext('2d');
    if (!context) return;

    const incomeColor = dark ? '#34d399' : '#10b981';
    const expenseColor = dark ? '#f87171' : '#ef4444';
    const gridColor = dark ? 'rgba(148, 163, 184, 0.12)' : 'rgba(100, 116, 139, 0.12)';
    const tickColor = dark ? '#94a3b8' : '#64748b';

    const gradient = context.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, dark ? 'rgba(52, 211, 153, 0.28)' : 'rgba(16, 185, 129, 0.24)');
    gradient.addColorStop(1, 'rgba(16, 185, 129, 0)');

    const config: ChartConfiguration<'line'> = {
      type: 'line',
      data: {
        labels: series.map((point) => cashflowLabel(point.label, unit)),
        datasets: [
          {
            label: 'Pemasukan',
            data: series.map((point) => point.income_cents),
            borderColor: incomeColor,
            backgroundColor: gradient,
            fill: true,
            tension: 0.38,
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 4,
            pointHoverBackgroundColor: incomeColor,
            pointHoverBorderColor: dark ? '#0f172a' : '#ffffff',
            pointHoverBorderWidth: 2
          },
          {
            label: 'Pengeluaran',
            data: series.map((point) => point.expense_cents),
            borderColor: expenseColor,
            backgroundColor: 'transparent',
            fill: false,
            tension: 0.38,
            borderWidth: 2,
            borderDash: [5, 4],
            pointRadius: 0,
            pointHoverRadius: 4,
            pointHoverBackgroundColor: expenseColor,
            pointHoverBorderColor: dark ? '#0f172a' : '#ffffff',
            pointHoverBorderWidth: 2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        animation: { duration: 450 },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: dark ? 'rgba(15, 23, 42, 0.96)' : 'rgba(15, 23, 42, 0.92)',
            titleColor: '#f8fafc',
            bodyColor: '#e2e8f0',
            padding: 12,
            cornerRadius: 10,
            displayColors: true,
            callbacks: {
              label: (item) =>
                ` ${item.dataset.label}: ${formatMoney(Number(item.raw), currentCurrency)}`
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            border: { display: false },
            ticks: {
              color: tickColor,
              maxTicksLimit: 8,
              maxRotation: 0,
              autoSkip: true,
              font: { size: 10 }
            }
          },
          y: {
            beginAtZero: true,
            grid: { color: gridColor },
            border: { display: false },
            ticks: {
              color: tickColor,
              maxTicksLimit: 5,
              font: { size: 10 },
              callback: (value) => formatMoney(Number(value), currentCurrency, { compact: true })
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

<div>
  <div class="mb-4 flex flex-wrap items-center gap-4">
    <span class="flex items-center gap-1.5 text-xs font-medium text-base-content/55">
      <span class="size-2 rounded-full bg-success"></span> Pemasukan
    </span>
    <span class="flex items-center gap-1.5 text-xs font-medium text-base-content/55">
      <span class="size-2 rounded-full bg-error"></span> Pengeluaran
    </span>
  </div>

  {#if loading}
    <div class="skeleton h-[280px] w-full rounded-xl"></div>
  {:else}
    <div class="chart-box relative">
      <canvas bind:this={canvas} aria-label="Grafik arus kas"></canvas>
      {#if total === 0}
        <div class="pointer-events-none absolute inset-0 grid place-items-center">
          <span class="rounded-full border border-base-content/8 bg-base-100/80 px-4 py-2 text-xs font-medium text-base-content/45 backdrop-blur">
            Belum ada arus kas pada periode ini
          </span>
        </div>
      {/if}
    </div>
  {/if}
</div>
