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
