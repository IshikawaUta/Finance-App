/**
 * Browser-only mock backend.
 *
 * It mirrors the Python IPC contract closely enough to develop and preview the
 * UI without Rust/Python (`npm run dev`). Data lives in localStorage and is
 * intentionally NOT secure — never used inside the packaged app.
 */

import type {
  AuthResponse,
  CategoriesResponse,
  DashboardFilters,
  DashboardResponse,
  HealthResponse,
  OkResponse,
  SystemStatus,
  Transaction,
  TransactionFilters,
  TransactionListResponse,
  User,
  Wallet,
  WalletListResponse
} from './types';

const DB_KEY = 'finance.mock.db.v1';
const SESSION_TTL_MS = 30 * 24 * 60 * 60 * 1000;

const INCOME_CATEGORIES = ['Gaji', 'Bonus', 'Freelance', 'Investasi', 'Hadiah', 'Lainnya'];
const EXPENSE_CATEGORIES = [
  'Makanan',
  'Transportasi',
  'Belanja',
  'Tagihan',
  'Kesehatan',
  'Hiburan',
  'Pendidikan',
  'Rumah',
  'Lainnya'
];

interface MockUser extends User {
  password: string;
}

interface MockWallet extends Wallet {
  user_id: string;
}

interface MockTransaction extends Omit<Transaction, 'wallet_name'> {
  user_id: string;
}

interface MockDB {
  users: MockUser[];
  wallets: MockWallet[];
  transactions: MockTransaction[];
}

let memoryDb: MockDB | null = null;

const delay = (ms = 90) => new Promise((resolve) => setTimeout(resolve, ms));
const rp = (amount: number) => Math.round(amount * 100);

function uid(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID();
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function error(code: string, message: string, details?: Record<string, unknown>): never {
  throw { code, message, details: details ?? {} };
}

function loadDb(): MockDB {
  if (typeof localStorage === 'undefined') {
    memoryDb ??= seedDatabase();
    return memoryDb;
  }
  const raw = localStorage.getItem(DB_KEY);
  if (raw) {
    try {
      const parsed = JSON.parse(raw) as MockDB;
      if (Array.isArray(parsed.users) && Array.isArray(parsed.wallets)) return parsed;
    } catch {
      // fall through to a fresh database
    }
  }
  const seeded = seedDatabase();
  localStorage.setItem(DB_KEY, JSON.stringify(seeded));
  return seeded;
}

function saveDb(db: MockDB): void {
  if (typeof localStorage === 'undefined') {
    memoryDb = db;
    return;
  }
  localStorage.setItem(DB_KEY, JSON.stringify(db));
}

function publicUser(user: MockUser): User {
  return {
    id: user.id,
    email: user.email,
    name: user.name,
    base_currency: user.base_currency,
    created_at: user.created_at
  };
}

function issueSession(user: MockUser): AuthResponse {
  return {
    token: `mock.${user.id}`,
    expires_at: new Date(Date.now() + SESSION_TTL_MS).toISOString(),
    user: publicUser(user)
  };
}

function requireUser(db: MockDB, token: unknown): MockUser {
  if (typeof token !== 'string' || !token.startsWith('mock.')) {
    error('AUTH_INVALID_TOKEN', 'Sesi tidak valid. Silakan masuk kembali.');
  }
  const user = db.users.find((candidate) => candidate.id === token.slice(5));
  if (!user) error('AUTH_INVALID_TOKEN', 'Sesi tidak valid. Silakan masuk kembali.');
  return user;
}

function walletBalance(db: MockDB, wallet: MockWallet): number {
  const delta = db.transactions
    .filter((tx) => tx.wallet_id === wallet.id)
    .reduce(
      (total, tx) => total + (tx.type === 'income' ? tx.amount_cents : -tx.amount_cents),
      0
    );
  return wallet.initial_balance_cents + delta;
}

function toPublicWallet(db: MockDB, wallet: MockWallet): Wallet {
  const { user_id: _userId, ...rest } = wallet;
  return { ...rest, balance_cents: walletBalance(db, wallet) };
}

function toPublicTx(db: MockDB, tx: MockTransaction): Transaction {
  const { user_id: _userId, ...rest } = tx;
  const wallet = db.wallets.find((candidate) => candidate.id === tx.wallet_id);
  return { ...rest, wallet_name: wallet?.name ?? 'Dompet dihapus' };
}

function listWallets(db: MockDB, userId: string): WalletListResponse {
  const wallets = db.wallets
    .filter((wallet) => wallet.user_id === userId && !wallet.archived)
    .sort((a, b) => a.created_at.localeCompare(b.created_at))
    .map((wallet) => toPublicWallet(db, wallet));
  return {
    wallets,
    total_balance_cents: wallets.reduce((total, wallet) => total + wallet.balance_cents, 0)
  };
}

// ---------------------------------------------------------------------------
// Date helpers (local time, matching the Python backend's configured timezone)
// ---------------------------------------------------------------------------

const startOfDay = (date: Date) => {
  const copy = new Date(date);
  copy.setHours(0, 0, 0, 0);
  return copy;
};

const addDays = (date: Date, days: number) => {
  const copy = new Date(date);
  copy.setDate(copy.getDate() + days);
  return copy;
};

const startOfMonth = (date: Date) => new Date(date.getFullYear(), date.getMonth(), 1);
const nextMonth = (date: Date) => new Date(date.getFullYear(), date.getMonth() + 1, 1);
const previousMonth = (date: Date) => new Date(date.getFullYear(), date.getMonth() - 1, 1);

function startOfWeek(date: Date): Date {
  const copy = startOfDay(date);
  const diff = (copy.getDay() + 6) % 7;
  return addDays(copy, -diff);
}

function localKey(date: Date): string {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function bucketStart(date: Date, granularity: 'day' | 'week' | 'month'): Date {
  if (granularity === 'week') return startOfWeek(date);
  if (granularity === 'month') return startOfMonth(date);
  return startOfDay(date);
}

function nextBucket(date: Date, granularity: 'day' | 'week' | 'month'): Date {
  if (granularity === 'week') return addDays(date, 7);
  if (granularity === 'month') return nextMonth(date);
  return addDays(date, 1);
}

interface DateRange {
  start: Date;
  end: Date;
  previousStart: Date;
  previousEnd: Date;
  granularity: 'day' | 'week' | 'month';
}

function parseDay(value: string | null | undefined): Date | null {
  if (!value) return null;
  const parsed = new Date(`${value.slice(0, 10)}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? null : startOfDay(parsed);
}

function periodRange(key: string, dateFrom?: string | null, dateTo?: string | null): DateRange {
  const today = startOfDay(new Date());
  let start: Date;
  let end: Date;
  let previousStart: Date;
  let previousEnd: Date;

  switch (key) {
    case 'this_week':
      start = startOfWeek(today);
      end = addDays(start, 7);
      previousStart = addDays(start, -7);
      previousEnd = start;
      break;
    case 'last_month':
      start = previousMonth(today);
      end = startOfMonth(today);
      previousStart = previousMonth(start);
      previousEnd = start;
      break;
    case 'last_7_days':
      start = addDays(today, -6);
      end = addDays(today, 1);
      previousStart = addDays(start, -7);
      previousEnd = start;
      break;
    case 'last_30_days':
      start = addDays(today, -29);
      end = addDays(today, 1);
      previousStart = addDays(start, -30);
      previousEnd = start;
      break;
    case 'this_year':
      start = new Date(today.getFullYear(), 0, 1);
      end = new Date(today.getFullYear() + 1, 0, 1);
      previousStart = new Date(today.getFullYear() - 1, 0, 1);
      previousEnd = start;
      break;
    case 'custom': {
      const from = parseDay(dateFrom);
      const to = parseDay(dateTo);
      if (!from || !to) error('VALIDATION_ERROR', 'Tanggal awal dan akhir wajib diisi.');
      if (from > to) error('VALIDATION_ERROR', 'Tanggal awal tidak boleh setelah tanggal akhir.');
      start = from;
      end = addDays(to, 1);
      const span = end.getTime() - start.getTime();
      previousEnd = start;
      previousStart = new Date(start.getTime() - span);
      break;
    }
    case 'this_month':
    default:
      start = startOfMonth(today);
      end = nextMonth(today);
      previousStart = previousMonth(today);
      previousEnd = start;
      break;
  }

  const days = Math.max(1, Math.round((end.getTime() - start.getTime()) / 86_400_000));
  const granularity = days <= 31 ? 'day' : days <= 120 ? 'week' : 'month';
  return { start, end, previousStart, previousEnd, granularity };
}

const inRange = (iso: string, start: Date, end: Date) => {
  const time = new Date(iso).getTime();
  return time >= start.getTime() && time < end.getTime();
};

const changePct = (current: number, previous: number): number | null => {
  if (previous === 0) return current === 0 ? 0 : 100;
  return Math.round(((current - previous) / previous) * 1000) / 10;
};

// ---------------------------------------------------------------------------
// Seed data
// ---------------------------------------------------------------------------

function createDemoData(
  db: MockDB,
  userId: string,
  baseCurrency: string
): { wallets: MockWallet[]; transactions: MockTransaction[] } {
  const now = new Date();
  const createdAt = now.toISOString();
  const walletSeeds: Array<[string, MockWallet['type'], number, string, string]> = [
    ['Dompet Tunai', 'cash', rp(750_000), '#10b981', 'wallet'],
    ['Bank Utama', 'bank', rp(8_500_000), '#3b82f6', 'bank'],
    ['E-Wallet', 'ewallet', rp(450_000), '#8b5cf6', 'phone']
  ];

  const wallets: MockWallet[] = walletSeeds.map(([name, type, initial, color, icon]) => ({
    id: uid(),
    user_id: userId,
    name,
    type,
    currency: baseCurrency,
    initial_balance_cents: initial,
    balance_cents: initial,
    color,
    icon,
    archived: false,
    created_at: createdAt,
    updated_at: createdAt
  }));

  const transactions: MockTransaction[] = [];
  const add = (
    wallet: MockWallet,
    type: MockTransaction['type'],
    amount: number,
    category: string,
    note: string,
    daysAgo: number,
    hour = 12
  ) => {
    const occurred = addDays(now, -daysAgo);
    occurred.setHours(hour, Math.floor(Math.random() * 60), 0, 0);
    transactions.push({
      id: uid(),
      user_id: userId,
      wallet_id: wallet.id,
      type,
      amount_cents: rp(amount),
      category,
      note,
      occurred_at: occurred.toISOString(),
      created_at: occurred.toISOString(),
      updated_at: occurred.toISOString()
    });
  };

  add(wallets[1], 'income', 9_500_000, 'Gaji', 'Gaji bulanan', 12, 9);
  add(wallets[2], 'income', 1_750_000, 'Freelance', 'Proyek desain', 6, 15);
  add(wallets[0], 'income', 500_000, 'Bonus', 'Bonus kecil', 21, 10);

  const expenseSeeds: Array<[string, string, number, number]> = [
    ['Makanan', 'Makan siang', 25_000, 75_000],
    ['Transportasi', 'Gojek / bensin', 15_000, 60_000],
    ['Belanja', 'Belanja bulanan', 80_000, 350_000],
    ['Tagihan', 'Listrik & internet', 100_000, 400_000],
    ['Kesehatan', 'Vitamin / obat', 40_000, 150_000],
    ['Hiburan', 'Langganan streaming', 30_000, 120_000],
    ['Pendidikan', 'Buku / kursus', 75_000, 250_000],
    ['Rumah', 'Perlengkapan rumah', 50_000, 200_000]
  ];

  for (let index = 0; index < 44; index += 1) {
    const [category, note, low, high] = expenseSeeds[Math.floor(Math.random() * expenseSeeds.length)];
    const amount = Math.round(low + Math.random() * (high - low));
    const wallet = wallets[Math.floor(Math.random() * wallets.length)];
    add(wallet, 'expense', amount, category, note, Math.floor(Math.random() * 75), 8 + (index % 12));
  }

  db.wallets.push(...wallets);
  db.transactions.push(...transactions);
  return { wallets, transactions };
}

function seedDatabase(): MockDB {
  const userId = uid();
  const createdAt = new Date().toISOString();
  const user: MockUser = {
    id: userId,
    email: 'demo@finance.app',
    name: 'Demo User',
    base_currency: 'IDR',
    created_at: createdAt,
    password: 'demo12345'
  };
  const db: MockDB = { users: [user], wallets: [], transactions: [] };
  createDemoData(db, userId, 'IDR');
  return db;
}

// ---------------------------------------------------------------------------
// Command handlers
// ---------------------------------------------------------------------------

function filterTransactions(db: MockDB, userId: string, filters: TransactionFilters): MockTransaction[] {
  const from = parseDay(filters.date_from);
  const to = parseDay(filters.date_to);
  const search = filters.search.trim().toLowerCase();

  return db.transactions
    .filter((tx) => tx.user_id === userId)
    .filter((tx) => !filters.wallet_ids.length || filters.wallet_ids.includes(tx.wallet_id))
    .filter((tx) => !filters.types.length || filters.types.includes(tx.type))
    .filter((tx) => !filters.categories.length || filters.categories.includes(tx.category))
    .filter((tx) => !from || new Date(tx.occurred_at) >= from)
    .filter((tx) => !to || new Date(tx.occurred_at) < addDays(to, 1))
    .filter(
      (tx) =>
        !search ||
        tx.note.toLowerCase().includes(search) ||
        tx.category.toLowerCase().includes(search)
    );
}

export async function mockInvoke<T>(command: string, body?: unknown): Promise<T> {
  await delay();
  const db = loadDb();
  const payload = (body ?? {}) as Record<string, unknown>;
  const token = payload.token;
  let result: unknown;

  switch (command) {
    case 'health': {
      result = { status: 'ok', version: '0.1.0-mock', uptime_seconds: 1 } satisfies HealthResponse;
      break;
    }

    case 'system_status':
    case 'config_set_mongodb': {
      result = {
        app_version: '0.1.0',
        python_version: 'mock',
        db_connected: true,
        db_latency_ms: 1.2,
        db_name: 'finance_app',
        db_uri_masked: 'mongodb+srv://demo:***@cluster.mongodb.net/?appName=FinanceApp',
        config_source: 'mock',
        data_dir: 'localStorage',
        last_error: null,
        offline: false
      } satisfies SystemStatus;
      break;
    }

    case 'auth_register': {
      const email = String(payload.email ?? '')
        .trim()
        .toLowerCase();
      const name = String(payload.name ?? '').trim();
      const password = String(payload.password ?? '');
      if (!email || !name || password.length < 8) {
        error('VALIDATION_ERROR', 'Nama, email, dan password (min. 8 karakter) wajib diisi.');
      }
      if (db.users.some((user) => user.email === email)) {
        error('AUTH_EMAIL_TAKEN', 'Email sudah terdaftar.');
      }
      const user: MockUser = {
        id: uid(),
        email,
        name,
        base_currency: String(payload.base_currency ?? 'IDR').toUpperCase(),
        created_at: new Date().toISOString(),
        password
      };
      db.users.push(user);
      result = issueSession(user);
      break;
    }

    case 'auth_login': {
      const email = String(payload.email ?? '')
        .trim()
        .toLowerCase();
      const user = db.users.find((candidate) => candidate.email === email);
      if (!user || user.password !== String(payload.password ?? '')) {
        error('AUTH_INVALID_CREDENTIALS', 'Email atau password salah.');
      }
      result = issueSession(user);
      break;
    }

    case 'auth_me': {
      result = publicUser(requireUser(db, token));
      break;
    }

    case 'auth_logout': {
      result = { ok: true, message: 'Berhasil keluar.' } satisfies OkResponse;
      break;
    }

    case 'wallet_list': {
      const user = requireUser(db, token);
      result = listWallets(db, user.id);
      break;
    }

    case 'wallet_create': {
      const user = requireUser(db, token);
      const name = String(payload.name ?? '').trim();
      if (!name) error('VALIDATION_ERROR', 'Nama dompet wajib diisi.');
      if (
        db.wallets.some(
          (wallet) => wallet.user_id === user.id && wallet.name.toLowerCase() === name.toLowerCase()
        )
      ) {
        error('WALLET_NAME_TAKEN', 'Nama dompet sudah digunakan.');
      }
      const now = new Date().toISOString();
      const wallet: MockWallet = {
        id: uid(),
        user_id: user.id,
        name,
        type: (payload.type as MockWallet['type']) ?? 'cash',
        currency: String(payload.currency ?? user.base_currency),
        initial_balance_cents: Number(payload.initial_balance_cents ?? 0),
        balance_cents: 0,
        color: String(payload.color ?? '#10b981'),
        icon: String(payload.icon ?? 'wallet'),
        archived: false,
        created_at: now,
        updated_at: now
      };
      db.wallets.push(wallet);
      result = toPublicWallet(db, wallet);
      break;
    }

    case 'wallet_update': {
      const user = requireUser(db, token);
      const wallet = db.wallets.find(
        (candidate) => candidate.id === payload.wallet_id && candidate.user_id === user.id
      );
      if (!wallet) error('NOT_FOUND', 'Dompet tidak ditemukan.');
      if (payload.name !== undefined) {
        const name = String(payload.name).trim();
        if (
          db.wallets.some(
            (candidate) =>
              candidate.id !== wallet.id &&
              candidate.user_id === user.id &&
              candidate.name.toLowerCase() === name.toLowerCase()
          )
        ) {
          error('WALLET_NAME_TAKEN', 'Nama dompet sudah digunakan.');
        }
        wallet.name = name;
      }
      if (payload.type !== undefined) wallet.type = payload.type as MockWallet['type'];
      if (payload.initial_balance_cents !== undefined) {
        wallet.initial_balance_cents = Number(payload.initial_balance_cents);
      }
      if (payload.color !== undefined) wallet.color = String(payload.color);
      if (payload.icon !== undefined) wallet.icon = String(payload.icon);
      if (payload.archived !== undefined) wallet.archived = Boolean(payload.archived);
      wallet.updated_at = new Date().toISOString();
      result = toPublicWallet(db, wallet);
      break;
    }

    case 'wallet_delete': {
      const user = requireUser(db, token);
      const wallet = db.wallets.find(
        (candidate) => candidate.id === payload.wallet_id && candidate.user_id === user.id
      );
      if (!wallet) error('NOT_FOUND', 'Dompet tidak ditemukan.');
      const count = db.transactions.filter((tx) => tx.wallet_id === wallet.id).length;
      if (count > 0 && !payload.delete_transactions) {
        error('WALLET_NOT_EMPTY', `Dompet masih memiliki ${count} transaksi.`, {
          transaction_count: count
        });
      }
      db.transactions = db.transactions.filter((tx) => tx.wallet_id !== wallet.id);
      db.wallets = db.wallets.filter((candidate) => candidate.id !== wallet.id);
      result = { ok: true, message: 'Dompet dihapus.' } satisfies OkResponse;
      break;
    }

    case 'transaction_list': {
      const user = requireUser(db, token);
      const filters: TransactionFilters = {
        wallet_ids: (payload.wallet_ids as string[]) ?? [],
        types: (payload.types as TransactionFilters['types']) ?? [],
        categories: (payload.categories as string[]) ?? [],
        date_from: (payload.date_from as string | null) ?? null,
        date_to: (payload.date_to as string | null) ?? null,
        search: String(payload.search ?? ''),
        page: Number(payload.page ?? 1),
        page_size: Number(payload.page_size ?? 25),
        sort_by: (payload.sort_by as TransactionFilters['sort_by']) ?? 'occurred_at',
        sort_dir: (payload.sort_dir as TransactionFilters['sort_dir']) ?? 'desc'
      };

      const filtered = filterTransactions(db, user.id, filters);
      const direction = filters.sort_dir === 'asc' ? 1 : -1;
      const sorted = [...filtered].sort((a, b) => {
        if (filters.sort_by === 'amount_cents') {
          return (a.amount_cents - b.amount_cents) * direction;
        }
        return a[filters.sort_by].localeCompare(b[filters.sort_by]) * direction;
      });

      const total = sorted.length;
      const start = (filters.page - 1) * filters.page_size;
      const items = sorted.slice(start, start + filters.page_size).map((tx) => toPublicTx(db, tx));
      const income = filtered
        .filter((tx) => tx.type === 'income')
        .reduce((sum, tx) => sum + tx.amount_cents, 0);
      const expense = filtered
        .filter((tx) => tx.type === 'expense')
        .reduce((sum, tx) => sum + tx.amount_cents, 0);

      result = {
        items,
        total,
        page: filters.page,
        page_size: filters.page_size,
        pages: total ? Math.ceil(total / filters.page_size) : 0,
        income_cents: income,
        expense_cents: expense
      } satisfies TransactionListResponse;
      break;
    }

    case 'transaction_create': {
      const user = requireUser(db, token);
      const wallet = db.wallets.find(
        (candidate) => candidate.id === payload.wallet_id && candidate.user_id === user.id
      );
      if (!wallet) error('NOT_FOUND', 'Dompet tidak ditemukan.');
      const amount = Number(payload.amount_cents ?? 0);
      if (!Number.isFinite(amount) || amount <= 0) {
        error('VALIDATION_ERROR', 'Nominal harus lebih dari nol.');
      }
      const now = new Date().toISOString();
      const tx: MockTransaction = {
        id: uid(),
        user_id: user.id,
        wallet_id: wallet.id,
        type: (payload.type as MockTransaction['type']) ?? 'expense',
        amount_cents: Math.round(amount),
        category: String(payload.category ?? 'Lainnya'),
        note: String(payload.note ?? ''),
        occurred_at: String(payload.occurred_at ?? now),
        created_at: now,
        updated_at: now
      };
      db.transactions.push(tx);
      result = toPublicTx(db, tx);
      break;
    }

    case 'transaction_update': {
      const user = requireUser(db, token);
      const tx = db.transactions.find(
        (candidate) => candidate.id === payload.transaction_id && candidate.user_id === user.id
      );
      if (!tx) error('NOT_FOUND', 'Transaksi tidak ditemukan.');
      if (payload.wallet_id !== undefined) {
        const wallet = db.wallets.find(
          (candidate) => candidate.id === payload.wallet_id && candidate.user_id === user.id
        );
        if (!wallet) error('NOT_FOUND', 'Dompet tidak ditemukan.');
        tx.wallet_id = wallet.id;
      }
      if (payload.type !== undefined) tx.type = payload.type as MockTransaction['type'];
      if (payload.amount_cents !== undefined) {
        tx.amount_cents = Number(payload.amount_cents);
      }
      if (payload.category !== undefined) tx.category = String(payload.category);
      if (payload.note !== undefined) tx.note = String(payload.note);
      if (payload.occurred_at !== undefined) tx.occurred_at = String(payload.occurred_at);
      tx.updated_at = new Date().toISOString();
      result = toPublicTx(db, tx);
      break;
    }

    case 'transaction_delete': {
      const user = requireUser(db, token);
      const exists = db.transactions.some(
        (tx) => tx.id === payload.transaction_id && tx.user_id === user.id
      );
      if (!exists) error('NOT_FOUND', 'Transaksi tidak ditemukan.');
      db.transactions = db.transactions.filter((tx) => tx.id !== payload.transaction_id);
      result = { ok: true, message: 'Transaksi dihapus.' } satisfies OkResponse;
      break;
    }

    case 'dashboard_get': {
      const user = requireUser(db, token);
      const filters = payload as unknown as DashboardFilters;
      const range = periodRange(filters.period, filters.date_from, filters.date_to);
      const walletFilter = filters.wallet_ids ?? [];

      const scoped = db.transactions
        .filter((tx) => tx.user_id === user.id)
        .filter((tx) => !walletFilter.length || walletFilter.includes(tx.wallet_id));

      const periodTx = scoped.filter((tx) => inRange(tx.occurred_at, range.start, range.end));
      const previousTx = scoped.filter((tx) =>
        inRange(tx.occurred_at, range.previousStart, range.previousEnd)
      );

      const sum = (items: MockTransaction[], type: MockTransaction['type']) =>
        items.filter((tx) => tx.type === type).reduce((total, tx) => total + tx.amount_cents, 0);

      const income = sum(periodTx, 'income');
      const expense = sum(periodTx, 'expense');
      const prevIncome = sum(previousTx, 'income');
      const prevExpense = sum(previousTx, 'expense');

      const buckets = new Map<string, { income: number; expense: number }>();
      for (
        let cursor = bucketStart(range.start, range.granularity);
        cursor < range.end;
        cursor = nextBucket(cursor, range.granularity)
      ) {
        buckets.set(localKey(cursor), { income: 0, expense: 0 });
      }
      for (const tx of periodTx) {
        const key = localKey(bucketStart(new Date(tx.occurred_at), range.granularity));
        const bucket = buckets.get(key);
        if (bucket) bucket[tx.type] += tx.amount_cents;
      }
      const cashflow = [...buckets.entries()].map(([key, values]) => ({
        bucket_start: new Date(`${key}T00:00:00`).toISOString(),
        label: key,
        income_cents: values.income,
        expense_cents: values.expense,
        net_cents: values.income - values.expense
      }));

      const categoryTotals = new Map<string, number>();
      for (const tx of periodTx.filter((item) => item.type === 'expense')) {
        categoryTotals.set(tx.category, (categoryTotals.get(tx.category) ?? 0) + tx.amount_cents);
      }
      const categoryTotal = [...categoryTotals.values()].reduce((a, b) => a + b, 0);
      let categorySlices = [...categoryTotals.entries()]
        .map(([category, amount]) => ({
          category,
          amount_cents: amount,
          percentage: categoryTotal ? Math.round((amount / categoryTotal) * 1000) / 10 : 0
        }))
        .sort((a, b) => b.amount_cents - a.amount_cents);

      if (categorySlices.length > 8) {
        const head = categorySlices.slice(0, 7);
        const rest = categorySlices.slice(7).reduce((total, item) => total + item.amount_cents, 0);
        const existing = head.find((item) => item.category === 'Lainnya');
        if (existing) {
          existing.amount_cents += rest;
          existing.percentage = categoryTotal
            ? Math.round((existing.amount_cents / categoryTotal) * 1000) / 10
            : 0;
        } else {
          head.push({
            category: 'Lainnya',
            amount_cents: rest,
            percentage: categoryTotal ? Math.round((rest / categoryTotal) * 1000) / 10 : 0
          });
        }
        categorySlices = head;
      }

      const wallets = listWallets(db, user.id);
      const recent = [...scoped]
        .sort((a, b) => b.occurred_at.localeCompare(a.occurred_at))
        .slice(0, 6)
        .map((tx) => toPublicTx(db, tx));

      result = {
        period: {
          key: filters.period,
          start: range.start.toISOString(),
          end: range.end.toISOString(),
          granularity: range.granularity
        },
        summary: {
          total_balance_cents: wallets.total_balance_cents,
          period_income_cents: income,
          period_expense_cents: expense,
          period_net_cents: income - expense,
          previous_income_cents: prevIncome,
          previous_expense_cents: prevExpense,
          income_change_pct: changePct(income, prevIncome),
          expense_change_pct: changePct(expense, prevExpense),
          wallet_count: wallets.wallets.length,
          transaction_count: periodTx.length
        },
        cashflow,
        expense_by_category: categorySlices,
        recent_transactions: recent,
        wallets: wallets.wallets
      } satisfies DashboardResponse;
      break;
    }

    case 'categories_list': {
      const user = requireUser(db, token);
      const used = db.transactions.filter((tx) => tx.user_id === user.id);
      const merge = (defaults: string[], type: MockTransaction['type']) => {
        const values = [...defaults];
        for (const tx of used.filter((item) => item.type === type)) {
          if (!values.includes(tx.category)) values.push(tx.category);
        }
        return values;
      };
      result = {
        income: merge(INCOME_CATEGORIES, 'income'),
        expense: merge(EXPENSE_CATEGORIES, 'expense')
      } satisfies CategoriesResponse;
      break;
    }

    case 'demo_seed': {
      const user = requireUser(db, token);
      if (db.wallets.some((wallet) => wallet.user_id === user.id)) {
        result = {
          ok: true,
          message: 'Data contoh hanya dapat dibuat pada akun tanpa dompet.'
        } satisfies OkResponse;
        break;
      }
      const created = createDemoData(db, user.id, user.base_currency);
      result = {
        ok: true,
        message: `Data contoh dibuat: ${created.wallets.length} dompet dan ${created.transactions.length} transaksi.`
      } satisfies OkResponse;
      break;
    }

    default:
      error('UNKNOWN_COMMAND', `Command mock tidak dikenal: ${command}`);
  }

  saveDb(db);
  return result as T;
}
