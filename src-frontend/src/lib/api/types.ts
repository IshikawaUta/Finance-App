export type PeriodKey =
  | 'this_week'
  | 'this_month'
  | 'last_month'
  | 'last_7_days'
  | 'last_30_days'
  | 'this_year'
  | 'custom';

export type WalletType = 'cash' | 'bank' | 'ewallet' | 'credit' | 'investment' | 'other';
export type TransactionType = 'income' | 'expense';
export type SortBy = 'occurred_at' | 'amount_cents' | 'created_at';
export type SortDir = 'asc' | 'desc';

export interface HealthResponse {
  status: string;
  version: string;
  uptime_seconds: number;
}

export interface SystemStatus {
  app_version: string;
  python_version: string;
  db_connected: boolean;
  db_latency_ms: number | null;
  db_name: string;
  db_uri_masked: string | null;
  config_source: string;
  data_dir: string;
  last_error: string | null;
  offline: boolean;
}

export interface User {
  id: string;
  email: string;
  name: string;
  base_currency: string;
  created_at: string;
}

export interface AuthResponse {
  token: string;
  expires_at: string;
  user: User;
}

export interface Wallet {
  id: string;
  name: string;
  type: WalletType;
  currency: string;
  initial_balance_cents: number;
  balance_cents: number;
  color: string;
  icon: string;
  archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface WalletListResponse {
  wallets: Wallet[];
  total_balance_cents: number;
}

export interface Transaction {
  id: string;
  wallet_id: string;
  wallet_name: string;
  type: TransactionType;
  amount_cents: number;
  category: string;
  note: string;
  occurred_at: string;
  created_at: string;
  updated_at: string;
}

export interface TransactionListResponse {
  items: Transaction[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  income_cents: number;
  expense_cents: number;
}

export interface PeriodInfo {
  key: string;
  start: string;
  end: string;
  granularity: 'day' | 'week' | 'month';
}

export interface Summary {
  total_balance_cents: number;
  period_income_cents: number;
  period_expense_cents: number;
  period_net_cents: number;
  previous_income_cents: number;
  previous_expense_cents: number;
  income_change_pct: number | null;
  expense_change_pct: number | null;
  wallet_count: number;
  transaction_count: number;
}

export interface CashflowPoint {
  bucket_start: string;
  label: string;
  income_cents: number;
  expense_cents: number;
  net_cents: number;
}

export interface CategorySlice {
  category: string;
  amount_cents: number;
  percentage: number;
}

export interface DashboardResponse {
  period: PeriodInfo;
  summary: Summary;
  cashflow: CashflowPoint[];
  expense_by_category: CategorySlice[];
  recent_transactions: Transaction[];
  wallets: Wallet[];
}

export interface CategoriesResponse {
  income: string[];
  expense: string[];
}

export interface OkResponse {
  ok: boolean;
  message: string;
}

export interface WalletInput {
  name: string;
  type: WalletType;
  currency: string;
  initial_balance_cents: number;
  color: string;
  icon: string;
}

export interface WalletUpdateInput {
  wallet_id: string;
  name?: string;
  type?: WalletType;
  initial_balance_cents?: number;
  color?: string;
  icon?: string;
  archived?: boolean;
}

export interface TransactionInput {
  wallet_id: string;
  type: TransactionType;
  amount_cents: number;
  category: string;
  note?: string;
  occurred_at?: string;
}

export interface TransactionUpdateInput {
  transaction_id: string;
  wallet_id?: string;
  type?: TransactionType;
  amount_cents?: number;
  category?: string;
  note?: string;
  occurred_at?: string;
}

export interface TransactionFilters {
  wallet_ids: string[];
  types: TransactionType[];
  categories: string[];
  date_from: string | null;
  date_to: string | null;
  search: string;
  page: number;
  page_size: number;
  sort_by: SortBy;
  sort_dir: SortDir;
}

export interface DashboardFilters {
  period: PeriodKey;
  date_from?: string | null;
  date_to?: string | null;
  wallet_ids?: string[];
}

export interface ApiErrorPayload {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface RegisterInput {
  email: string;
  name: string;
  password: string;
  base_currency: string;
}

export interface LoginInput {
  email: string;
  password: string;
}
