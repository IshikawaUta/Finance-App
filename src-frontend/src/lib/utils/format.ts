const LOCALE = 'id-ID';

export function formatMoney(
  cents: number,
  currency = 'IDR',
  options: { compact?: boolean; signed?: boolean } = {}
): string {
  const value = cents / 100;
  const formatter = new Intl.NumberFormat(LOCALE, {
    style: 'currency',
    currency,
    notation: options.compact ? 'compact' : 'standard',
    minimumFractionDigits: currency === 'IDR' ? 0 : 2,
    maximumFractionDigits: options.compact ? 1 : currency === 'IDR' ? 0 : 2
  });

  const formatted = formatter.format(Math.abs(value));
  if (!options.signed) return value < 0 ? `-${formatted}` : formatted;
  return value < 0 ? `−${formatted}` : `+${formatted}`;
}

export function formatNumber(value: number, maximumFractionDigits = 0): string {
  return new Intl.NumberFormat(LOCALE, { maximumFractionDigits }).format(value);
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  const sign = value > 0 ? '+' : '';
  return `${sign}${new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 1 }).format(value)}%`;
}

export function formatDate(iso: string | Date): string {
  const date = typeof iso === 'string' ? new Date(iso) : iso;
  return new Intl.DateTimeFormat(LOCALE, {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  }).format(date);
}

export function formatDateLong(iso: string | Date = new Date()): string {
  const date = typeof iso === 'string' ? new Date(iso) : iso;
  return new Intl.DateTimeFormat(LOCALE, {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric'
  }).format(date);
}

export function formatDateShort(iso: string | Date): string {
  const date = typeof iso === 'string' ? new Date(iso) : iso;
  return new Intl.DateTimeFormat(LOCALE, { day: 'numeric', month: 'short' }).format(date);
}

export function formatDateTime(iso: string | Date): string {
  const date = typeof iso === 'string' ? new Date(iso) : iso;
  return new Intl.DateTimeFormat(LOCALE, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date);
}

export function formatRelative(iso: string): string {
  const date = new Date(iso);
  const today = new Date();
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const diff = Math.round((start.getTime() - target.getTime()) / 86_400_000);

  if (diff === 0) return 'Hari ini';
  if (diff === 1) return 'Kemarin';
  if (diff > 1 && diff < 7) return `${diff} hari lalu`;
  return formatDate(date);
}

export function toDateInputValue(iso: string | Date = new Date()): string {
  const date = typeof iso === 'string' ? new Date(iso) : iso;
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function todayInputValue(): string {
  return toDateInputValue(new Date());
}

/** Keep the original time-of-day when editing; use now for new transactions. */
export function combineDateWithTime(dateValue: string, originalIso?: string | null): string {
  const base = originalIso ? new Date(originalIso) : new Date();
  const [year, month, day] = dateValue.split('-').map(Number);
  base.setFullYear(year, month - 1, day);
  return base.toISOString();
}

export function initials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('');
}

export function parseAmountToCents(input: string): number {
  const digits = input.replace(/[^\d]/g, '');
  if (!digits) return 0;
  return Number(digits) * 100;
}

export function centsToInput(cents: number): string {
  if (!cents) return '';
  return formatNumber(Math.round(cents / 100));
}
