from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


def filter_report(
    report: pd.DataFrame,
    cantons: Iterable[str] | None = None,
    sectors: Iterable[str] | None = None,
    priority_bands: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Filter an analyzed company report without mutating the original DataFrame."""
    result = report.copy()

    if cantons:
        result = result[result["canton"].isin(cantons)]

    if sectors:
        result = result[result["sector"].isin(sectors)]

    if priority_bands:
        result = result[result["priority_band"].isin(priority_bands)]

    return result.reset_index(drop=True)
