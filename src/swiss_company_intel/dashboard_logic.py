from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


def filter_report(
    report: pd.DataFrame,
    cantons: Iterable[str] | None = None,
    sectors: Iterable[str] | None = None,
    priority_bands: Iterable[str] | None = None,
    company_query: str = "",
    min_attention_score: float | None = None,
) -> pd.DataFrame:
    """Filter an analyzed company report without mutating the original DataFrame."""
    result = report.copy()

    query = company_query.strip()
    if query:
        result = result[result["company"].str.contains(query, case=False, regex=False, na=False)]

    if cantons:
        result = result[result["canton"].isin(cantons)]

    if sectors:
        result = result[result["sector"].isin(sectors)]

    if priority_bands:
        result = result[result["priority_band"].isin(priority_bands)]

    if min_attention_score is not None:
        if not isinstance(min_attention_score, (int, float)) or not 0 <= min_attention_score <= 100:
            raise ValueError("min_attention_score must be between 0 and 100")
        result = result[result["attention_score"] >= min_attention_score]

    return result.reset_index(drop=True)


def report_to_csv_bytes(report: pd.DataFrame) -> bytes:
    """Serialize the displayed report to UTF-8 CSV without a DataFrame index."""
    return report.to_csv(index=False).encode("utf-8-sig")


def history_chart_data(history: pd.DataFrame) -> pd.DataFrame:
    """Use the unique run ID as the historical score chart axis."""
    return history.sort_values("run_id").set_index("run_id")[["attention_score"]].copy()
