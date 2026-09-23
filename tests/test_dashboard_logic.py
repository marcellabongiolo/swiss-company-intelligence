import pandas as pd

from swiss_company_intel.dashboard_logic import filter_report


def sample_report() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "company": "Alpha AG",
                "canton": "ZH",
                "sector": "Technology",
                "priority_band": "high",
            },
            {
                "company": "Beta SA",
                "canton": "VD",
                "sector": "Technology",
                "priority_band": "low",
            },
            {
                "company": "Gamma AG",
                "canton": "ZH",
                "sector": "Industrial",
                "priority_band": "moderate",
            },
        ]
    )


def test_filter_report_by_canton():
    result = filter_report(sample_report(), cantons=["ZH"])

    assert result["company"].tolist() == ["Alpha AG", "Gamma AG"]


def test_filter_report_combines_filters():
    result = filter_report(
        sample_report(),
        cantons=["ZH"],
        sectors=["Technology"],
        priority_bands=["high"],
    )

    assert result["company"].tolist() == ["Alpha AG"]


def test_filter_report_without_filters_keeps_all_rows():
    result = filter_report(sample_report())

    assert len(result) == 3
