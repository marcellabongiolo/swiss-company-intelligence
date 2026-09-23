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
