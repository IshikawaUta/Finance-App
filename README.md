# FinanceApp

A cross-platform personal finance desktop app for Windows, macOS and Linux.

- **Shell:** [PyTauri](https://pytauri.github.io/) 0.8 (Tauri 2 + embedded Python 3.12)
- **Frontend:** SvelteKit 2 / Svelte 5, TypeScript, TailwindCSS 4, DaisyUI 5, Chart.js 4
- **Backend:** Python 3.12, Beanie + PyMongo async, MongoDB Atlas
- **Auth:** Argon2id passwords and HS256 JWTs (30 days)
- **CI/CD:** GitHub Actions matrix builds `.exe`, `.deb` / `.AppImage`, and `.dmg`

FinanceApp stores money as integer minor units (`amount_cents`) and keeps all
IPC field names in `snake_case` on both sides of the bridge.

## Features

- Email/password registration and login, persistent session, offline session cache
- Multiple wallets (cash, bank, e-wallet, credit, investment, other)
- Income/expense CRUD with automatic wallet balances
- Transaction history with wallet, type, category, date and text filters
- Dashboard with month/week/custom summaries, cashflow line chart and expense pie chart
- Light/dark themes, responsive desktop layout, toast notifications, skeleton states
- Browser mock backend for UI work without Rust/Python
- First-run MongoDB setup on the login screen, plus Settings to test, persist
  and switch the connection at runtime

## Project layout

```
finance-app/
├── src-python/finance_app/     # Python backend (IPC commands, services, Beanie models)
├── src-frontend/               # SvelteKit static frontend
├── src-tauri/                  # Tauri/PyTauri Rust shell
│   ├── src/lib.rs              # Extension module exported to Python
│   ├── src/main.rs             # Standalone embedded-Python entry point
│   ├── tauri.conf.json         # Window, CSP, bundle metadata
│   └── tauri.bundle.json       # Adds the portable Python runtime to bundles
├── scripts/prepare_pyembed.py  # Download PBS + install backend into pyembed
├── scripts/generate_icons.py   # Reproducible app/favicon artwork
├── docs/ipc-contract.md        # Command-by-command IPC contract
├── docs/architecture.md        # Architecture and design decisions
└── .github/workflows/build.yml # Lint/test + 4-platform release build
```

## Quick start (UI only, no Rust/Python)

The frontend automatically falls back to a localStorage mock backend when it is
not running inside Tauri:

```bash
npm install
npm run install:frontend
npm run dev
# open http://localhost:1420
```

Demo credentials: `demo@finance.app` / `demo12345`.

## Local development with the real backend

Prerequisites: Python 3.12, Node.js 20.19+ or 22.12+ (CI uses Node 22), Rust
stable, and the [Tauri system dependencies](https://tauri.app/start/prerequisites/)
for your OS.

```bash
python3 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
PYTAURI_STANDALONE=1 pip install -e .

npm install
npm run install:frontend
cp .env.example .env                # fill in your MongoDB Atlas URI
npm run tauri dev
```

`tauri dev` launches the Rust binary, which runs the Python package from the
active virtualenv (or `<repo>/.venv`). `PYTAURI_STANDALONE=1` prevents
`setup.py` from trying to build the Python extension module, which is not
needed by the standalone dev binary.

### Ubuntu 24.04 desktop notes

Install the native dependencies and Rust once:

```bash
sudo apt install build-essential pkg-config libwebkit2gtk-4.1-dev \
  libayatana-appindicator3-dev librsvg2-dev patchelf libssl-dev libxdo-dev \
  libfuse2t64 python3.12-venv
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
```

Then launch the desktop app with:

```bash
npm run desktop
```

`npm run desktop` is a small wrapper around `tauri dev`. It removes GTK/GIO
environment variables leaked by the Snap build of VS Code; those variables make
WebKitGTK load incompatible `core20` libraries. It also sets
`WEBKIT_DISABLE_COMPOSITING_MODE=1`, which avoids a blank window on some
Wayland/NVIDIA setups. From a normal terminal, `npm run tauri dev` works too.

Ubuntu's `gnome-settings-daemon` 46 moved the XSettings `antialiasing`,
`hinting`, and `rgba-order` keys into a `.deprecated` schema, but GTK3/WebKitGTK
still reads them from the main schema. If the app exits with
`Settings schema 'org.gnome.settings-daemon.plugins.xsettings' does not contain
a key named 'antialiasing'`, add the keys to a user schema override:

```bash
mkdir -p ~/.local/share/glib-2.0/schemas
cp /usr/share/glib-2.0/schemas/org.gnome.settings-daemon.enums.xml \
  ~/.local/share/glib-2.0/schemas/
# Copy the xsettings schema and move the three keys from the
# `.deprecated` schema into the main schema, then:
glib-compile-schemas ~/.local/share/glib-2.0/schemas
```

If you prefer to run the Python process directly (`python -m finance_app`),
install the extension module instead:

```bash
pip install -e .                    # builds finance_app.ext_mod with cargo
python -m finance_app
```

The extension module path is only for that workflow; release builds compile it
into the Rust binary.

### Configuration

`.env` is loaded in development and is gitignored. In production, GitHub Actions
sets `FINANCE_MONGODB_URI`, `FINANCE_MONGODB_DB`, and `FINANCE_TIMEZONE`;
`src-tauri/src/lib.rs` bakes those three into the binary with `option_env!` and
only sets environment variables that are not already present; `config.json`
still has the highest priority. `FINANCE_JWT_SECRET` and `FINANCE_LOG_LEVEL`
are runtime variables and are not baked.

| Variable              | Default        | Purpose                                                                    |
| --------------------- | -------------- | -------------------------------------------------------------------------- |
| `FINANCE_MONGODB_URI` | —              | Atlas connection string                                                    |
| `FINANCE_MONGODB_DB`  | `finance_app`  | Database name                                                              |
| `FINANCE_JWT_SECRET`  | generated      | JWT signing key (min. 32 chars). Leave empty for a unique per-install key. |
| `FINANCE_TIMEZONE`    | `Asia/Jakarta` | Day/month boundary timezone                                                |
| `FINANCE_LOG_LEVEL`   | `INFO`         | `DEBUG`, `INFO`, `WARNING`, `ERROR`                                        |

For the MongoDB URI, database name and timezone, runtime precedence is
**app-data `config.json` → environment → defaults**. The login setup dialog and
Settings page write `config.json` with owner-only permissions (`chmod 600` on
Unix). The MongoDB URI is never logged or returned unmasked.

When no URI is configured, the login screen opens the database setup dialog
automatically. The same dialog is available through the **Atur** button. It
tests the connection, saves it, and reloads the app. On Windows the file is
written to `%LOCALAPPDATA%\FinanceApp\config.json`.

## Production build

The bundled Python runtime is a [python-build-standalone](https://github.com/astral-sh/python-build-standalone)
distribution. Download/extract it and install the backend into it:

```bash
python3 scripts/prepare_pyembed.py
```

Then set the PyO3 interpreter and platform linker flags, and build with the
dedicated bundle profile:

```bash
export PYO3_PYTHON=$(realpath src-tauri/pyembed/python/bin/python3)

# Linux
export RUSTFLAGS="-C link-arg=-Wl,-rpath,\$ORIGIN/../lib/FinanceApp/lib -C link-arg=-Wl,-rpath,\$ORIGIN/../lib -L $(realpath src-tauri/pyembed/python/lib)"

# macOS
export RUSTFLAGS="-C link-arg=-Wl,-rpath,@executable_path/../Resources/lib -L $(realpath src-tauri/pyembed/python/lib)"
install_name_tool -id '@rpath/libpython3.12.dylib' src-tauri/pyembed/python/lib/libpython3.12.dylib

npm run tauri -- build --config=src-tauri/tauri.bundle.json -- --profile bundle-release
```

On Windows, set `PYO3_PYTHON` to `src-tauri\pyembed\python\python.exe` and omit
`RUSTFLAGS`. Installers are written to
`src-tauri/target/bundle-release/bundle/`; the exact set depends on the host OS
(for example `nsis` on Windows, `dmg` on macOS, and `deb`/`appimage` on Linux).
CI builds those four formats explicitly.

`bundle-release` keeps the embedded Python environment out of
`target/release`, so `tauri dev` keeps using your virtualenv.

## CI/CD and releases

`.github/workflows/build.yml` runs on pushes, pull requests, version tags and
manual dispatch:

1. Ruff + pytest + Svelte check + static frontend build
2. Native builds on Ubuntu 22.04, Windows, macOS 15 ARM and macOS 15 Intel
3. A published GitHub Release for the tag, with the installers attached

The bundle formats are explicit:

| Platform          | Output                                |
| ----------------- | ------------------------------------- |
| Windows           | NSIS installer `.exe`                 |
| Linux             | Debian package `.deb` and `.AppImage` |
| macOS ARM / Intel | `.dmg`                                |

Create a release by pushing a tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The workflow builds all four matrix jobs and creates the GitHub Release for
`v0.1.0`. You can also run **Actions → Build desktop releases → Run workflow**
and enter a tag in `release_tag`; the same tag is created and populated.

Add the MongoDB URI as the repository secret **`FINANCE_MONGODB_URI`**. It is
only available to trusted builds; fork pull requests build without it and the
app shows the database setup screen.

> **Security:** a connection string embedded in a desktop binary can be
> extracted by a determined user. Use a dedicated Atlas database user with
> `readWrite` on only the `finance_app` database, rotate its password
> periodically, and prefer the runtime override on the login setup screen or in
> Settings when distributing to untrusted users. Never commit `.env`.

## Database

Collections are created on first write:

- `users` — unique `email`, Argon2id password hash
- `wallets` — owner, type, currency, initial balance, color, icon
- `transactions` — owner, wallet, type, `amount_cents`, category, note, timestamps

Balances are derived: `initial_balance_cents + income − expense`. Deleting a
wallet with transactions requires `delete_transactions: true`; otherwise the
backend rejects the operation with `WALLET_NOT_EMPTY`.

## Troubleshooting

| Symptom                                | Fix                                                                                                                             |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `svelte-kit: not found`                | Run `npm run install:frontend` (dependencies live in `src-frontend`).                                                           |
| `Python virtual environment not found` | Create `.venv` and install the project, or activate a venv before `tauri dev`.                                                  |
| `No pytauri entry point is found`      | You ran `python -m finance_app` without building `ext_mod`; run `pip install -e .` without `PYTAURI_STANDALONE=1`.              |
| Database status shows disconnected     | Check the Atlas IP allow-list and password. Use the **Atur** button on the login screen or Settings → Database to test a new URI. |
| Blank window after a release build     | Rebuild with `--profile bundle-release` and confirm `src-tauri/pyembed/python` exists.                                          |

## License

MIT
