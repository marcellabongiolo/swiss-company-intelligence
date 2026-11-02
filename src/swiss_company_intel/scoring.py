from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import fields

import numpy as np
import pandas as pd

from .models import ScoreWeights


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return float(max(low, min(high, value)))


def linear_risk(value: float, safe: float, severe: float, higher_is_worse: bool = True) -> float:
    if not all(math.isfinite(threshold) for threshold in (safe, severe)):
        raise ValueError("safe and severe thresholds must be finite")
    if higher_is_worse and safe >= severe:
        raise ValueError("safe must be lower than severe when higher is worse")
    if not higher_is_worse and safe <= severe:
        raise ValueError("safe must be higher than severe when lower is worse")

    if higher_is_worse:
        return clamp((value - safe) / (severe - safe))

    return clamp((safe - value) / (safe - severe))


def robust_zscore(series: pd.Series) -> pd.Series:
    values = series.astype(float)
    median = float(values.median())
    mad = float(np.median(np.abs(values - median)))

    if math.isclose(mad, 0.0, abs_tol=1e-12):
        if (values == median).all():
            return pd.Series(np.zeros(len(values)), index=series.index, dtype=float)
        # When most values equal the median, MAD cannot provide a scale.
        # Mark deviations as anomalous rather than silently reporting all zeros.
        return pd.Series(
            np.where(values == median, 0.0, np.sign(values - median) * 3.5),
            index=series.index,
            dtype=float,
        )

    return 0.67448975 * (values - median) / mad


def anomaly_strength(zscores: Iterable[float], threshold: float = 2.5) -> float:
    max_abs = max((abs(float(z)) for z in zscores), default=0.0)
    if max_abs <= threshold:
        return 0.0
    return clamp((max_abs - threshold) / 3.5)


def score_row(row: pd.Series, weights: ScoreWeights | None = None) -> tuple[float, list[str]]:
    weights = weights or ScoreWeights()
    for field in fields(ScoreWeights):
        value = getattr(weights, field.name)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f"Score weight {field.name} must be finite and nonnegative")
    if not math.isclose(weights.total(), 100.0, abs_tol=1e-9):
        raise ValueError(f"Score weights must add up to 100, got {weights.total()}")

    reasons: list[str] = []

    leverage = linear_risk(row["debt_to_equity"], safe=0.8, severe=3.0)
    if leverage >= 0.35:
        reasons.append(f"elevated leverage ({row['debt_to_equity']:.2f}x D/E)")

    liquidity = linear_risk(row["current_ratio"], safe=1.8, severe=0.7, higher_is_worse=False)
    if liquidity >= 0.35:
        reasons.append(f"weak liquidity ({row['current_ratio']:.2f} current ratio)")

    concentration = linear_risk(row["customer_concentration_pct"], safe=15.0, severe=55.0)
    if concentration >= 0.35:
        reasons.append(f"customer concentration ({row['customer_concentration_pct']:.1f}%)")

    late_payment = linear_risk(row["late_payment_pct"], safe=8.0, severe=35.0)
    if late_payment >= 0.35:
        reasons.append(f"late-payment exposure ({row['late_payment_pct']:.1f}%)")

    revenue_decline = linear_risk(
        row["revenue_growth_pct"], safe=4.0, severe=-18.0, higher_is_worse=False
    )
    if revenue_decline >= 0.35:
        reasons.append(f"revenue pressure ({row['revenue_growth_pct']:.1f}% YoY)")

    employee_decline = linear_risk(
        row["employee_growth_pct"], safe=3.0, severe=-15.0, higher_is_worse=False
    )
    if employee_decline >= 0.35:
        reasons.append(f"workforce contraction ({row['employee_growth_pct']:.1f}% YoY)")

    anomaly = float(row.get("sector_anomaly_strength", 0.0))
    if not math.isfinite(anomaly) or not 0.0 <= anomaly <= 1.0:
        raise ValueError("sector_anomaly_strength must be finite and between 0 and 1")
    if anomaly >= 0.25:
        reasons.append("unusual sector-relative metrics")

    score = (
        leverage * weights.leverage
        + liquidity * weights.liquidity
        + concentration * weights.concentration
        + late_payment * weights.late_payment
        + revenue_decline * weights.revenue_decline
        + employee_decline * weights.employee_decline
        + anomaly * weights.anomaly
    )

    return round(clamp(score / 100.0) * 100.0, 1), reasons
