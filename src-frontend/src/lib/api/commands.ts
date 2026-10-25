import { invoke } from './client';
import type {
  AuthResponse,
  CategoriesResponse,
  DashboardFilters,
  DashboardResponse,
  HealthResponse,
  LoginInput,
  OkResponse,
  RegisterInput,
  SystemStatus,
  Transaction,
  TransactionFilters,
  TransactionInput,
  TransactionListResponse,
  TransactionUpdateInput,
  User,
  Wallet,
  WalletInput,
  WalletListResponse,
  WalletUpdateInput
} from './types';

const token = (value: string) => ({ token: value });

export const api = {
  health: () => invoke<HealthResponse>('health'),

  systemStatus: () => invoke<SystemStatus>('system_status'),

  setMongoConnection: (uri: string, db_name: string) =>
    invoke<SystemStatus>('config_set_mongodb', { uri, db_name }),

  register: (input: RegisterInput) => invoke<AuthResponse>('auth_register', input),

  login: (input: LoginInput) => invoke<AuthResponse>('auth_login', input),

  me: (authToken: string) => invoke<User>('auth_me', token(authToken)),

  logout: (authToken: string) => invoke<OkResponse>('auth_logout', token(authToken)),

  listWallets: (authToken: string) =>
    invoke<WalletListResponse>('wallet_list', token(authToken)),

  createWallet: (authToken: string, input: WalletInput) =>
    invoke<Wallet>('wallet_create', { ...token(authToken), ...input }),

  updateWallet: (authToken: string, input: WalletUpdateInput) =>
    invoke<Wallet>('wallet_update', { ...token(authToken), ...input }),

  deleteWallet: (authToken: string, walletId: string, deleteTransactions = false) =>
    invoke<OkResponse>('wallet_delete', {
      ...token(authToken),
      wallet_id: walletId,
      delete_transactions: deleteTransactions
    }),

  listTransactions: (authToken: string, filters: TransactionFilters) =>
    invoke<TransactionListResponse>('transaction_list', { ...token(authToken), ...filters }),

  createTransaction: (authToken: string, input: TransactionInput) =>
    invoke<Transaction>('transaction_create', { ...token(authToken), ...input }),

  updateTransaction: (authToken: string, input: TransactionUpdateInput) =>
    invoke<Transaction>('transaction_update', { ...token(authToken), ...input }),

  deleteTransaction: (authToken: string, transactionId: string) =>
    invoke<OkResponse>('transaction_delete', {
      ...token(authToken),
      transaction_id: transactionId
    }),

  dashboard: (authToken: string, filters: DashboardFilters) =>
    invoke<DashboardResponse>('dashboard_get', { ...token(authToken), ...filters }),

  categories: (authToken: string) =>
    invoke<CategoriesResponse>('categories_list', token(authToken)),

  seedDemo: (authToken: string) => invoke<OkResponse>('demo_seed', token(authToken))
};
