"""Domain constants shared by the backend."""

from __future__ import annotations

from typing import Final

APP_NAME: Final = "FinanceApp"
APP_VERSION: Final = "0.1.0"

WALLET_TYPES: Final = ("cash", "bank", "ewallet", "credit", "investment", "other")
TRANSACTION_TYPES: Final = ("income", "expense")

DEFAULT_WALLET_COLORS: Final = (
    "#10b981",
    "#3b82f6",
    "#8b5cf6",
    "#f59e0b",
    "#ef4444",
    "#06b6d4",
    "#ec4899",
    "#64748b",
)

DEFAULT_CATEGORIES: Final = {
    "income": (
        "Gaji",
        "Bonus",
        "Freelance",
        "Investasi",
        "Hadiah",
        "Lainnya",
    ),
    "expense": (
        "Makanan",
        "Transportasi",
        "Belanja",
        "Tagihan",
        "Kesehatan",
        "Hiburan",
        "Pendidikan",
        "Rumah",
        "Lainnya",
    ),
}
