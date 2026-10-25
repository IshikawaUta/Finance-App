import type { PeriodKey } from '$lib/api/types';

export const PERIOD_OPTIONS: Array<{ value: PeriodKey; label: string }> = [
  { value: 'this_month', label: 'Bulan ini' },
  { value: 'last_month', label: 'Bulan lalu' },
  { value: 'this_week', label: 'Minggu ini' },
  { value: 'last_7_days', label: '7 hari terakhir' },
  { value: 'last_30_days', label: '30 hari terakhir' },
  { value: 'this_year', label: 'Tahun ini' },
  { value: 'custom', label: 'Rentang kustom' }
];

export function periodLabel(key: string): string {
  return PERIOD_OPTIONS.find((option) => option.value === key)?.label ?? 'Periode';
}

export function cashflowLabel(label: string, granularity: 'day' | 'week' | 'month'): string {
  const date = new Date(`${label.slice(0, 10)}T00:00:00`);
  if (granularity === 'month') {
    return new Intl.DateTimeFormat('id-ID', { month: 'short', year: '2-digit' }).format(date);
  }
  return new Intl.DateTimeFormat('id-ID', { day: 'numeric', month: 'short' }).format(date);
}

export function rangeLabel(startIso: string, endIso: string): string {
  const start = new Date(startIso);
  const end = new Date(new Date(endIso).getTime() - 1);
  const sameYear = start.getFullYear() === end.getFullYear();
  const startText = new Intl.DateTimeFormat('id-ID', {
    day: 'numeric',
    month: 'short',
    ...(sameYear ? {} : { year: 'numeric' })
  }).format(start);
  const endText = new Intl.DateTimeFormat('id-ID', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  }).format(end);
  return `${startText} – ${endText}`;
}
