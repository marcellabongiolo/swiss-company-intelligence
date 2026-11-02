import pandas as pd

from swiss_company_intel.scoring import linear_risk, robust_zscore, score_row


def test_linear_risk_higher_is_worse():
    assert linear_risk(0.8, safe=0.8, severe=3.0) == 0.0
    assert linear_risk(3.0, safe=0.8, severe=3.0) == 1.0


def test_linear_risk_lower_is_worse():
    assert linear_risk(1.8, safe=1.8, severe=0.7, higher_is_worse=False) == 0.0
    assert linear_risk(0.7, safe=1.8, severe=0.7, higher_is_worse=False) == 1.0


def test_robust_zscore_constant_series():
    z = robust_zscore(pd.Series([5, 5, 5, 5]))
    assert (z == 0).all()


def test_score_row_flags_risky_company():
    row = pd.Series(
        {
            "debt_to_equity": 3.0,
            "current_ratio": 0.7,
            "customer_concentration_pct": 55.0,
            "late_payment_pct": 35.0,
            "revenue_growth_pct": -18.0,
            "employee_growth_pct": -15.0,
            "sector_anomaly_strength": 1.0,
        }
    )
    score, reasons = score_row(row)
    assert score == 100.0
    assert len(reasons) >= 5


def test_robust_zscore_flags_outlier_when_mad_is_zero():
    scores = robust_zscore(pd.Series([10.0, 10.0, 10.0, 1000.0]))
    assert (scores.iloc[:3] == 0).all()
    assert scores.iloc[3] > 2.5


def test_score_row_rejects_invalid_direct_weights():
    import pytest
    from swiss_company_intel.models import ScoreWeights

    row = pd.Series({
        "debt_to_equity": 1.0, "current_ratio": 1.8,
        "customer_concentration_pct": 15.0, "late_payment_pct": 8.0,
        "revenue_growth_pct": 4.0, "employee_growth_pct": 3.0,
    })
    for weights in (
        ScoreWeights(leverage=-1.0, liquidity=35.0),
        ScoreWeights(leverage=float("nan")),
        ScoreWeights(leverage=float("inf")),
    ):
        with pytest.raises(ValueError, match="finite and nonnegative"):
            score_row(row, weights)


def test_linear_risk_rejects_invalid_threshold_order():
    import pytest

    with pytest.raises(ValueError, match="lower than severe"):
        linear_risk(2.0, safe=3.0, severe=1.0)
    with pytest.raises(ValueError, match="higher than severe"):
        linear_risk(2.0, safe=1.0, severe=3.0, higher_is_worse=False)
    with pytest.raises(ValueError, match="lower than severe"):
        linear_risk(2.0, safe=1.0, severe=1.0)
    with pytest.raises(ValueError, match="finite"):
        linear_risk(2.0, safe=float("nan"), severe=3.0)


def test_score_row_rejects_invalid_anomaly_strength():
    import pytest

    base = {
        "debt_to_equity": 0.8,
        "current_ratio": 1.8,
        "customer_concentration_pct": 15.0,
        "late_payment_pct": 8.0,
        "revenue_growth_pct": 4.0,
        "employee_growth_pct": 3.0,
    }
    for invalid in (-0.1, 1.1, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="sector_anomaly_strength"):
            score_row(pd.Series(base | {"sector_anomaly_strength": invalid}))


def test_linear_risk_rejects_nonfinite_values():
    import pytest

    for invalid in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="risk value must be finite"):
            linear_risk(invalid, safe=0.8, severe=3.0)
        with pytest.raises(ValueError, match="risk value must be finite"):
            linear_risk(invalid, safe=1.8, severe=0.7, higher_is_worse=False)


def test_anomaly_strength_rejects_nonfinite_zscores_and_thresholds():
    import pytest
    from swiss_company_intel.scoring import anomaly_strength

    for invalid in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="z-scores must be finite"):
            anomaly_strength([0.0, invalid])
        with pytest.raises(ValueError, match="threshold must be finite"):
            anomaly_strength([1.0], threshold=invalid)
    with pytest.raises(ValueError, match="threshold must be finite and nonnegative"):
        anomaly_strength([1.0], threshold=-1.0)
    assert anomaly_strength([0.0, 2.5]) == 0.0
