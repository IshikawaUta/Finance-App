"""FinanceApp — personal finance desktop application backend.

The package is intentionally import-light: importing :mod:`finance_app` must
not import PyTauri, so unit tests can run without the Rust extension module.
"""

__version__ = "0.1.0"
__all__ = ["__version__"]
