from __future__ import annotations

from pathlib import Path

import pandas as pd

from .models import REQUIRED_COLUMNS, SWISS_CANTONS

NUMERIC_COLUMNS = [
    "revenue_m_chf",
    "revenue_growth_pct",
    "ebitda_margin_pct",
    "debt_to_equity",
    "current_ratio",
    "employee_growth_pct",
    "customer_concentration_pct",
    "late_payment_pct",
]


def load_companies(path: str | Path) -> pd.DataFrame:
    """Load, normalize and validate a company dataset."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    df = df.copy()
    for column in ("company", "canton", "sector"):
        df[column] = df[column].astype(str).str.strip()

    df["canton"] = df["canton"].str.upper()

    invalid_cantons = sorted(set(df.loc[~df["canton"].isin(SWISS_CANTONS), "canton"]))
    if invalid_cantons:
        raise ValueError(f"Invalid Swiss canton code(s): {', '.join(invalid_cantons)}")

    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    if df[NUMERIC_COLUMNS].isna().any().any():
        bad = df[NUMERIC_COLUMNS].isna().sum()
        bad = bad[bad > 0].to_dict()
        raise ValueError(f"Non-numeric or missing values in numeric columns: {bad}")

    if (df["revenue_m_chf"] < 0).any():
        raise ValueError("revenue_m_chf cannot be negative")

    for pct_col in ("customer_concentration_pct", "late_payment_pct"):
        if ((df[pct_col] < 0) | (df[pct_col] > 100)).any():
            raise ValueError(f"{pct_col} must be between 0 and 100")

    return df
