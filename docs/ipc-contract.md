# IPC contract

All calls go through PyTauri's JSON IPC bridge. The frontend wrapper
(`src/lib/api/client.ts`) calls `pyInvoke(command, body)` in Tauri and lazily
uses a localStorage mock in a normal browser.

- Every request is a single JSON object (never positional arguments).
- Every response is a JSON object with `snake_case` fields.
- Authenticated commands carry the JWT in the request body as `token`.
- Money is always an integer amount in minor units (`amount_cents`).
- Timestamps are ISO-8601 strings with an explicit UTC offset (`Z` for UTC).
- Dates (`date_from`, `date_to`) are `YYYY-MM-DD` strings.

## Errors

A failed command rejects with a **string** containing JSON:

```json
{
  "code": "DB_UNAVAILABLE",
  "message": "Tidak dapat terhubung ke database…",
  "details": { "error": "ServerSelectionTimeoutError" }
}
```

`ApiError` in `client.ts` parses that string. Known codes:

| Code | Meaning |
| --- | --- |
| `AUTH_INVALID_TOKEN` | Signature/format invalid, or the token points to a missing user |
| `AUTH_EXPIRED` | Token past `exp` |
| `AUTH_INVALID_CREDENTIALS` | Wrong email/password |
| `AUTH_EMAIL_TAKEN` | Registration email already exists |
| `DB_UNAVAILABLE` | MongoDB unreachable or operation failed |
| `NOT_FOUND` | Wallet or transaction missing, or owned by another user |
| `WALLET_NAME_TAKEN` | Duplicate wallet name for this user |
| `WALLET_NOT_EMPTY` | Delete needs `delete_transactions: true` |
| `WALLET_ARCHIVED` | The wallet is archived and cannot receive transactions |
| `UNSUPPORTED_CURRENCY` | Wallet currency differs from the account currency |
| `VALIDATION_ERROR` | Invalid ID, filter or Pydantic payload; see `details` |
| `INTERNAL` | Unexpected backend error |

## System

### `health`

No request body.

```json
{ "status": "ok", "version": "0.1.0", "uptime_seconds": 12.4 }
```

### `system_status`

No request body. Never returns credentials.

```json
{
  "app_version": "0.1.0",
  "python_version": "3.12.15",
  "db_connected": true,
  "db_latency_ms": 42.1,
  "db_name": "finance_app",
  "db_uri_masked": "mongodb+srv://user:***@cluster.example.net/",
  "config_source": "file",
  "data_dir": "/home/me/.local/share/FinanceApp",
  "last_error": null,
  "offline": false
}
```

`config_source` is `file`, `env`, `missing` or `mock` (browser mock only).

### `config_set_mongodb`

Tests the URI, writes app-data `config.json`, reconnects, and returns the new
`system_status`. This command is available before authentication so the login
screen can be used for first-run database setup.

```json
{ "uri": "mongodb+srv://user:password@cluster.example.net/", "db_name": "finance_app" }
```

`uri` must start with `mongodb://` or `mongodb+srv://`; `db_name` must match
`^[A-Za-z0-9_-]{1,64}$`.

## Authentication

### `auth_register`

```json
{ "email": "me@example.com", "name": "Me", "password": "min-8-chars", "base_currency": "IDR" }
```

Returns `AuthResponse`:

```json
{
  "token": "eyJ…",
  "expires_at": "2026-11-23T10:00:00Z",
  "user": { "id": "…", "email": "me@example.com", "name": "Me", "base_currency": "IDR", "created_at": "…" }
}
```

### `auth_login`

```json
{ "email": "me@example.com", "password": "min-8-chars" }
```

Returns `AuthResponse`.

### `auth_me`

```json
{ "token": "eyJ…" }
```

Returns `User`:

```json
{ "id": "…", "email": "me@example.com", "name": "Me", "base_currency": "IDR", "created_at": "…" }
```

### `auth_logout`

```json
{ "token": "eyJ…" }
```

Returns `{ "ok": true, "message": "Berhasil keluar." }`. Logout is stateless:
the client discards the token.

## Wallets

### `wallet_list`

```json
{ "token": "eyJ…" }
```

Returns:

```json
{
  "wallets": [
    {
      "id": "…",
      "name": "Dompet utama",
      "type": "cash",
      "currency": "IDR",
      "initial_balance_cents": 500000,
      "balance_cents": 425000,
      "color": "#10b981",
      "icon": "wallet",
      "archived": false,
      "created_at": "…",
      "updated_at": "…"
    }
  ],
  "total_balance_cents": 425000
}
```

### `wallet_create`

```json
{
  "token": "eyJ…",
  "name": "Tabungan",
  "type": "bank",
  "currency": "IDR",
  "initial_balance_cents": 0,
  "color": "#3b82f6",
  "icon": "wallet"
}
```

`type` is one of `cash`, `bank`, `ewallet`, `credit`, `investment`, `other`.
`initial_balance_cents` is `0..10^15`. Returns `Wallet`.

### `wallet_update`

```json
{
  "token": "eyJ…",
  "wallet_id": "…",
  "name": "Tabungan utama",
  "archived": false
}
```

All fields except `token` and `wallet_id` are optional. Returns `Wallet`.

### `wallet_delete`

```json
{ "token": "eyJ…", "wallet_id": "…", "delete_transactions": false }
```

Returns `{ "ok": true, "message": "…" }`. If transactions exist and
`delete_transactions` is false, rejects with `WALLET_NOT_EMPTY`.

## Transactions

### `transaction_list`

```json
{
  "token": "eyJ…",
  "wallet_ids": [],
  "types": [],
  "categories": [],
  "date_from": "2026-10-01",
  "date_to": "2026-10-31",
  "search": "kopi",
  "page": 1,
  "page_size": 25,
  "sort_by": "occurred_at",
  "sort_dir": "desc"
}
```

All filters are optional except `token`. `sort_by` is `occurred_at`,
`amount_cents` or `created_at`; `page_size` is `1..200`. Returns:

```json
{
  "items": [
    {
      "id": "…",
      "wallet_id": "…",
      "wallet_name": "Dompet utama",
      "type": "expense",
      "amount_cents": 25000,
      "category": "Makanan",
      "note": "Kopi",
      "occurred_at": "2026-10-24T08:30:00Z",
      "created_at": "…",
      "updated_at": "…"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 25,
  "pages": 1,
  "income_cents": 0,
  "expense_cents": 25000
}
```

`income_cents` and `expense_cents` summarize the filtered set, not only the
current page.

### `transaction_create`

```json
{
  "token": "eyJ…",
  "wallet_id": "…",
  "type": "expense",
  "amount_cents": 25000,
  "category": "Makanan",
  "note": "Kopi",
  "occurred_at": "2026-10-24T08:30:00Z"
}
```

`occurred_at` is optional (defaults to now). Returns `Transaction`.

### `transaction_update`

```json
{
  "token": "eyJ…",
  "transaction_id": "…",
  "amount_cents": 30000,
  "category": "Makanan"
}
```

All fields except `token` and `transaction_id` are optional. Returns
`Transaction`.

### `transaction_delete`

```json
{ "token": "eyJ…", "transaction_id": "…" }
```

Returns `{ "ok": true, "message": "…" }`.

## Dashboard & metadata

### `dashboard_get`

```json
{
  "token": "eyJ…",
  "period": "this_month",
  "date_from": null,
  "date_to": null,
  "wallet_ids": []
}
```

`period` is `this_week`, `this_month`, `last_month`, `last_7_days`,
`last_30_days`, `this_year` or `custom`. For `custom`, provide `date_from` and
`date_to`. Returns:

```json
{
  "period": { "key": "this_month", "start": "2026-10-01T00:00:00Z", "end": "2026-11-01T00:00:00Z", "granularity": "day" },
  "summary": {
    "total_balance_cents": 425000,
    "period_income_cents": 800000,
    "period_expense_cents": 375000,
    "period_net_cents": 425000,
    "previous_income_cents": 700000,
    "previous_expense_cents": 300000,
    "income_change_pct": 14.29,
    "expense_change_pct": 25.0,
    "wallet_count": 2,
    "transaction_count": 18
  },
  "cashflow": [
    { "bucket_start": "2026-10-01T00:00:00Z", "label": "1 Okt", "income_cents": 0, "expense_cents": 25000, "net_cents": -25000 }
  ],
  "expense_by_category": [
    { "category": "Makanan", "amount_cents": 25000, "percentage": 100.0 }
  ],
  "recent_transactions": [],
  "wallets": []
}
```

`total_balance_cents` always covers all active wallets, even when
`wallet_ids` filters the period charts and summaries.

### `categories_list`

```json
{ "token": "eyJ…" }
```

Returns `{ "income": ["Gaji", …], "expense": ["Makanan", …] }`, merging default
categories with categories already used by the account.

### `demo_seed`

```json
{ "token": "eyJ…" }
```

Only works when the account has no wallets. Returns
`{ "ok": true, "message": "…" }`.
