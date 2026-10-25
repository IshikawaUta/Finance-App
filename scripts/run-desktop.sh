#!/usr/bin/env bash
# Launch the desktop app from a normal terminal or from VS Code's integrated
# terminal. The latter runs inside a Snap and exports GTK/GIO paths that make
# WebKitGTK load the Snap's old core20 libraries, so strip those variables.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# VS Code (Snap) leaks these into the integrated terminal.
unset GIO_MODULE_DIR GIO_LAUNCHED_DESKTOP_FILE GIO_LAUNCHED_DESKTOP_FILE_PID
unset GTK_PATH GTK_EXE_PREFIX GTK_IM_MODULE_FILE GTK_MODULES
unset GSETTINGS_SCHEMA_DIR GDK_BACKEND LOCPATH

# Restore the host's data dirs when launched from the VS Code Snap.
if [[ -n "${XDG_DATA_DIRS_VSCODE_SNAP_ORIG:-}" ]]; then
  export XDG_DATA_DIRS="$XDG_DATA_DIRS_VSCODE_SNAP_ORIG"
fi

# WebKitGTK 2.52 + GTK3 can crash on some Wayland/NVIDIA combinations.
export WEBKIT_DISABLE_COMPOSITING_MODE="${WEBKIT_DISABLE_COMPOSITING_MODE:-1}"

if ! command -v cargo >/dev/null 2>&1 && [[ -f "$HOME/.cargo/env" ]]; then
  # shellcheck disable=SC1091
  source "$HOME/.cargo/env"
fi

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "Python virtualenv not found at $ROOT/.venv" >&2
  echo "Create it with: python3 -m venv .venv && PYTAURI_STANDALONE=1 .venv/bin/pip install -e ." >&2
  exit 1
fi

exec npm run tauri dev
