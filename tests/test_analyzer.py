import pandas as pd

from swiss_company_intel.analyzer import CompanyAnalyzer


def test_analyzer_sorts_highest_score_first():
    df = pd.DataFrame(
        [
            {
                "company": "Stable AG",
                "canton": "ZH",
                "sector": "Software",
                "revenue_m_chf": 100,
                "revenue_growth_pct": 8,
                "ebitda_margin_pct": 24,
                "debt_to_equity": 0.4,
                "current_ratio": 2.2,
                "employee_growth_pct": 7,
                "customer_concentration_pct": 12,
                "late_payment_pct": 5,
            },
            {
                "company": "Watch AG",
                "canton": "ZG",
                "sector": "Software",
                "revenue_m_chf": 70,
                "revenue_growth_pct": -20,
                "ebitda_margin_pct": 2,
                "debt_to_equity": 3.2,
                "current_ratio": 0.6,
                "employee_growth_pct": -18,
                "customer_concentration_pct": 60,
                "late_payment_pct": 40,
            },
        ]
    )

    result = CompanyAnalyzer().analyze(df)
    assert result.iloc[0]["company"] == "Watch AG"
    assert result.iloc[0]["attention_score"] > result.iloc[1]["attention_score"]


def test_analyzer_rejects_invalid_revenue():
    import pytest

    valid = {
        "company": "Example AG", "canton": "ZH", "sector": "Software",
        "revenue_m_chf": 100.0, "revenue_growth_pct": 4.0,
        "ebitda_margin_pct": 15.0, "debt_to_equity": 0.8,
        "current_ratio": 1.8, "employee_growth_pct": 3.0,
        "customer_concentration_pct": 15.0, "late_payment_pct": 8.0,
    }
    for invalid in (-1.0, float("nan"), float("inf"), "invalid"):
        with pytest.raises(ValueError, match="revenue_m_chf"):
            CompanyAnalyzer().analyze(pd.DataFrame([valid | {"revenue_m_chf": invalid}]))


def test_analyzer_rejects_invalid_percentage_metrics():
    import pytest

    valid = {
        "company": "Example AG", "canton": "ZH", "sector": "Software",
        "revenue_m_chf": 100.0, "revenue_growth_pct": 4.0,
        "ebitda_margin_pct": 15.0, "debt_to_equity": 0.8,
        "current_ratio": 1.8, "employee_growth_pct": 3.0,
        "customer_concentration_pct": 15.0, "late_payment_pct": 8.0,
    }
    for column in ("customer_concentration_pct", "late_payment_pct"):
        for invalid in (-1.0, 100.1, float("nan"), float("inf"), "invalid"):
            with pytest.raises(ValueError, match=column):
                CompanyAnalyzer().analyze(pd.DataFrame([valid | {column: invalid}]))


def test_analyzer_reports_missing_required_metric():
    import pytest

    report = pd.DataFrame([{
        "company": "Example AG", "sector": "Software",
        "revenue_growth_pct": 4.0, "ebitda_margin_pct": 15.0,
        "debt_to_equity": 0.8, "current_ratio": 1.8,
        "employee_growth_pct": 3.0, "customer_concentration_pct": 15.0,
        "late_payment_pct": 8.0,
    }])
    with pytest.raises(ValueError, match="Dataset missing required columns: debt_to_equity"):
        CompanyAnalyzer().analyze(report.drop(columns="debt_to_equity"))


def test_analyzer_rejects_nonnumeric_and_nonfinite_anomaly_metrics():
    import pytest

    valid = {
        "company": "Example AG", "sector": "Software",
        "revenue_growth_pct": 4.0, "ebitda_margin_pct": 15.0,
        "debt_to_equity": 0.8, "current_ratio": 1.8,
        "employee_growth_pct": 3.0, "customer_concentration_pct": 15.0,
        "late_payment_pct": 8.0,
    }
    for column in ("revenue_growth_pct", "ebitda_margin_pct", "debt_to_equity", "current_ratio", "employee_growth_pct"):
        for invalid in ("bad", None, float("inf")):
            with pytest.raises(ValueError, match=f"{column} must contain finite numeric values"):
                CompanyAnalyzer().analyze(pd.DataFrame([valid | {column: invalid}]))
