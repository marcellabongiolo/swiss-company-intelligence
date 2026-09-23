from __future__ import annotations

from dataclasses import dataclass

REQUIRED_COLUMNS = {
    "company",
    "canton",
    "sector",
    "revenue_m_chf",
    "revenue_growth_pct",
    "ebitda_margin_pct",
    "debt_to_equity",
    "current_ratio",
    "employee_growth_pct",
    "customer_concentration_pct",
    "late_payment_pct",
}

SWISS_CANTONS = {
    "AG", "AI", "AR", "BE", "BL", "BS", "FR", "GE", "GL", "GR", "JU",
    "LU", "NE", "NW", "OW", "SG", "SH", "SO", "SZ", "TG", "TI", "UR",
    "VD", "VS", "ZG", "ZH",
}


@dataclass(frozen=True)
class ScoreWeights:
    leverage: float = 18.0
    liquidity: float = 16.0
    concentration: float = 18.0
    late_payment: float = 14.0
    revenue_decline: float = 12.0
    employee_decline: float = 8.0
    anomaly: float = 14.0

    def total(self) -> float:
        return sum(
            (
                self.leverage,
                self.liquidity,
                self.concentration,
                self.late_payment,
                self.revenue_decline,
                self.employee_decline,
                self.anomaly,
            )
        )
