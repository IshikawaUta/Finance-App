# Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│ SvelteKit static frontend (WebView)                         │
│  routes, stores, components, Chart.js                       │
│  lib/api/client.ts ── pyInvoke ──┐                          │
└──────────────────────────────────┼──────────────────────────┘
                                   │ JSON IPC
┌──────────────────────────────────▼──────────────────────────┐
│ Rust shell (Tauri 2 + PyTauri 0.8)                          │
│  src/lib.rs   extension module / context + builder factories│
│  src/main.rs  embedded Python interpreter (release)         │
└──────────────────────────────────┬──────────────────────────┘
                                   │ Python calls
┌──────────────────────────────────▼──────────────────────────┐
│ Python backend                                               │
│  commands.py  thin IPC adapters + auth                       │
│  services.py  wallet, transaction, dashboard logic           │
│  auth.py      Argon2id + HS256 JWT                           │
│  database.py  PyMongo AsyncMongoClient + Beanie init         │
│  state.py     config, connection lifecycle, status           │
│  models.py    Beanie documents and indexes                   │
└──────────────────────────────────┬──────────────────────────┘
                                   │ async driver
                            MongoDB Atlas
```

The Python package root is deliberately import-light: `finance_app/__init__.py`
does not import PyTauri, so domain modules and tests can run without the
compiled Rust extension. The IPC/bootstrap modules (`commands.py`, `main.py`)
import PyTauri at module level; error serialization imports it lazily.

## Request lifecycle

1. A Svelte component calls a typed helper in `lib/api/commands.ts`.
2. `lib/api/client.ts` chooses `pyInvoke` (Tauri) or the localStorage mock.
3. PyTauri invokes the matching `@commands.command()` in `commands.py`.
4. The command ensures the database is connected, validates the JWT, and calls
   a service.
5. Services query Beanie documents and return Pydantic response models.
6. PyTauri serializes the response to JSON; the frontend updates its stores.
7. Errors are converted by `api_errors()` into a JSON string rejection that
   `ApiError` parses on the frontend.

The blocking portal in `main.py` owns one asyncio loop for the whole app. IPC
handlers are async and use `anyio.to_thread` for CPU-bound Argon2 work so the
loop stays responsive.

## Data model

### User

- `email` (unique, lowercased), `name`, `password_hash`, `base_currency`
- `created_at`, `updated_at`, `last_login_at`
- Passwords: Argon2id (`argon2-cffi`), verified off the event loop.

### Wallet

- Owner (`user_id`), `name`, `type`, `currency`
- `initial_balance_cents`, `color`, `icon`, `archived`
- `balance_cents` is computed from the initial balance plus all transactions.

### Transaction

- Owner, `wallet_id`, `type` (`income` | `expense`)
- `amount_cents` (positive integer), `category`, `note`, `occurred_at`
- Indexed by owner + wallet + `occurred_at` for history and dashboard queries.

All money is stored as integer minor units. This avoids floating-point drift
and keeps aggregation deterministic. Currency is a display concern; FinanceApp
does not perform FX conversion.

## Configuration & secrets

MongoDB and timezone settings precedence, highest first:

1. `config.json` in the OS app-data directory (written by the login setup
   dialog and Settings)
2. Environment variables (`.env` in dev; compile-time injection in CI)
3. Built-in defaults

`FINANCE_MONGODB_URI`, `FINANCE_MONGODB_DB` and `FINANCE_TIMEZONE` are injected
into the Rust binary at build time through `option_env!` and copied into the
process environment by `src-tauri/src/lib.rs` only when the corresponding
variable is not already set. The login setup dialog and Settings screen test a
new URI before persisting it, then swap the live connection and reload the UI.
`config.json` and `jwt.key` are written with owner-only permissions.

The JWT secret is either `FINANCE_JWT_SECRET` (≥32 chars) or a random
`jwt.key` generated per installation. Tokens are HS256, 30-day expiry, and
contain only the user id plus standard claims.

## Frontend state

- **auth** — token in `localStorage`, cached user for offline startup.
- **wallets / transactions / dashboard** — cached stores with loading and
  error states. Pages load on mount and after mutations.
- **system** — database status, polled periodically; drives the offline banner,
  login setup status and Settings diagnostics.
- **ui** — theme (persisted and applied before first paint), toasts, global
  data-version counter used to invalidate dashboard data after mutations.

The browser mock (`lib/api/mock.ts`) mirrors the same command names and
response shapes with localStorage, so the UI can be developed with `npm run
dev` and no backend.

## Security notes

- Never log or return the raw MongoDB URI; `config.mask_uri()` redacts the
  password in `system_status`, and validation/error/log paths call
  `redact_uri_passwords()` before serialization.
- IPC commands validate ownership before mutating wallets/transactions.
- Pydantic rejects unknown request fields (`extra="forbid"`), reducing the
  surface for accidental contract drift.
- The Tauri window uses a restrictive CSP and no remote content.
- A connection string embedded in a distributed binary is extractable. Use a
  dedicated least-privilege Atlas user and rotate credentials; prefer runtime
  configuration for broad distribution.

## Performance

- Dashboard data is fetched in one IPC call rather than several.
- Indexes cover owner/wallet/date queries and the unique user email.
- Frontend charts are tree-shaken Chart.js modules registered once.
- Static SvelteKit output is served from the Tauri asset protocol. The backend
  still attempts a bounded Atlas connection at startup (up to about 10 seconds);
  if it fails, the app opens in offline mode and the frontend can show a cached
  session.
