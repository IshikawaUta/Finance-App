"""Build the PyTauri Rust extension module for direct Python development.

Running ``python -m finance_app`` imports ``finance_app.ext_mod``, a compiled
extension module that exports the Tauri builder/context factories. The normal
``tauri dev`` and release flows instead run an embedded interpreter and do not
need this module, so it must NOT be built for them (set
``PYTAURI_STANDALONE=1``).

Reference: https://pytauri.github.io/pytauri/latest/usage/tutorial/using-pytauri/
"""

from __future__ import annotations

import os

from setuptools import setup
from setuptools_rust import RustExtension

STANDALONE = os.environ.get("PYTAURI_STANDALONE") == "1"

setup(
    rust_extensions=[]
    if STANDALONE
    else [
        RustExtension(
            # Must match `[project.entry-points.pytauri].ext_mod`
            target="finance_app.ext_mod",
            path="src-tauri/Cargo.toml",
            features=[
                "pyo3/extension-module",
                # Embed frontend assets instead of using the dev server.
                "tauri/custom-protocol",
            ],
            debug=os.environ.get("FINANCE_DEBUG_BUILD") == "1",
        )
    ],
)
