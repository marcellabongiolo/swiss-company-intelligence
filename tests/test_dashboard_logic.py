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


def test_company_search_is_case_insensitive_and_trims_query():
    result = filter_report(sample_report(), company_query="  alpha  ")
    assert result["company"].tolist() == ["Alpha AG"]


def test_company_search_combines_with_existing_filters():
    result = filter_report(sample_report(), company_query="a", cantons=["VD"])
    assert result["company"].tolist() == ["Beta SA"]


def test_company_search_treats_regex_symbols_literally():
    report = sample_report()
    report.loc[0, "company"] = "A.B AG"
    assert filter_report(report, company_query=".").company.tolist() == ["A.B AG"]


def test_company_search_does_not_mutate_original():
    report = sample_report()
    original = report.copy(deep=True)
    filter_report(report, company_query="alpha")
    pd.testing.assert_frame_equal(report, original)
