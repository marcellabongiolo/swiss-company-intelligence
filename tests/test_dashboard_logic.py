import pandas as pd

from swiss_company_intel.dashboard_logic import filter_report, history_chart_data, report_to_csv_bytes


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


def test_minimum_attention_score_includes_boundary_and_combines_filters():
    report = sample_report()
    report["attention_score"] = [75.0, 30.0, 90.0]
    result = filter_report(report, cantons=["ZH"], min_attention_score=75.0)
    assert result["company"].tolist() == ["Alpha AG", "Gamma AG"]


def test_minimum_attention_score_can_return_empty_without_mutation():
    report = sample_report()
    report["attention_score"] = [75.0, 30.0, 90.0]
    original = report.copy(deep=True)
    assert filter_report(report, min_attention_score=100.0).empty
    pd.testing.assert_frame_equal(report, original)


def test_minimum_attention_score_rejects_invalid_thresholds():
    import pytest

    for threshold in (-1, 101, float("nan"), "bad"):
        with pytest.raises(ValueError, match="min_attention_score"):
            filter_report(sample_report(), min_attention_score=threshold)


def test_filtered_csv_export_preserves_selected_rows_and_columns():
    from io import BytesIO

    report = sample_report()
    filtered = filter_report(report, cantons=["ZH"])
    original = filtered.copy(deep=True)
    payload = report_to_csv_bytes(filtered)
    assert isinstance(payload, bytes)
    decoded = pd.read_csv(BytesIO(payload))
    pd.testing.assert_frame_equal(decoded, filtered)
    pd.testing.assert_frame_equal(filtered, original)
    assert "Unnamed: 0" not in decoded.columns


def test_history_chart_uses_unique_run_ids_when_timestamps_match():
    history = pd.DataFrame({
        "run_id": [3, 1, 2],
        "created_at": ["2026-11-03 12:00:00"] * 3,
        "attention_score": [75.0, 30.0, 60.0],
    })
    original = history.copy(deep=True)
    chart = history_chart_data(history)
    assert chart.index.tolist() == [1, 2, 3]
    assert chart["attention_score"].tolist() == [30.0, 60.0, 75.0]
    assert chart.index.is_unique
    pd.testing.assert_frame_equal(history, original)
