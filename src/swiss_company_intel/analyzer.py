from __future__ import annotations

import pandas as pd

from .models import ScoreWeights
from .scoring import anomaly_strength, robust_zscore, score_row


ANOMALY_COLUMNS = [
    "revenue_growth_pct",
    "ebitda_margin_pct",
    "debt_to_equity",
    "current_ratio",
    "employee_growth_pct",
    "customer_concentration_pct",
    "late_payment_pct",
]


class CompanyAnalyzer:
    """Build sector-relative features and calculate explainable attention scores."""

    def __init__(self, weights: ScoreWeights | None = None) -> None:
        self.weights = weights or ScoreWeights()

    def _add_sector_zscores(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()

        for column in ANOMALY_COLUMNS:
            z_name = f"z_{column}"
            result[z_name] = (
                result.groupby("sector", group_keys=False)[column]
                .transform(robust_zscore)
                .astype(float)
            )

        z_columns = [f"z_{c}" for c in ANOMALY_COLUMNS]
        result["sector_anomaly_strength"] = result[z_columns].apply(
            lambda row: anomaly_strength(row.values),
            axis=1,
        )
        return result

    def analyze(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            raise ValueError("Dataset is empty")

        result = self._add_sector_zscores(df)

        scored = result.apply(
            lambda row: score_row(row, self.weights),
            axis=1,
            result_type="expand",
        )
        result["attention_score"] = scored[0].astype(float)
        result["reasons"] = scored[1].apply(
            lambda reasons: "; ".join(reasons) if reasons else "no major signal"
        )

        result["priority_band"] = pd.cut(
            result["attention_score"],
            bins=[-0.1, 25, 50, 75, 100],
            labels=["low", "moderate", "high", "critical"],
        ).astype(str)

        result["sector_rank"] = (
            result.groupby("sector")["attention_score"]
            .rank(method="dense", ascending=False)
            .astype(int)
        )

        return result.sort_values(
            ["attention_score", "company"],
            ascending=[False, True],
        ).reset_index(drop=True)

    def report_columns(self, analyzed: pd.DataFrame) -> pd.DataFrame:
        return analyzed[
            [
                "company",
                "canton",
                "sector",
                "attention_score",
                "priority_band",
                "sector_rank",
                "revenue_growth_pct",
                "ebitda_margin_pct",
                "debt_to_equity",
                "current_ratio",
                "customer_concentration_pct",
                "late_payment_pct",
                "sector_anomaly_strength",
                "reasons",
            ]
        ].copy()
