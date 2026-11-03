import pandas as pd
import pytest

from swiss_company_intel.persistence import AnalysisStore


def sample_report() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "company": "Alpha AG",
                "canton": "ZH",
                "sector": "Technology",
                "attention_score": 72.5,
                "priority_band": "high",
                "reasons": "elevated leverage",
            },
            {
                "company": "Beta SA",
                "canton": "VD",
                "sector": "Industrial",
                "attention_score": 22.0,
                "priority_band": "low",
                "reasons": "no major signal",
            },
        ]
    )


def test_save_and_list_runs(tmp_path):
    store = AnalysisStore(tmp_path / "history.db")

    run_id = store.save_analysis(sample_report(), source="test")
    runs = store.list_runs()

    assert run_id == 1
    assert runs.iloc[0]["source"] == "test"
    assert runs.iloc[0]["company_count"] == 2


def test_company_history_across_runs(tmp_path):
    store = AnalysisStore(tmp_path / "history.db")
    first = sample_report()
    second = sample_report()
    second.loc[second["company"] == "Alpha AG", "attention_score"] = 81.0
    second.loc[second["company"] == "Alpha AG", "priority_band"] = "critical"

    store.save_analysis(first, source="first")
    store.save_analysis(second, source="second")

    history = store.company_history("Alpha AG")

    assert history["attention_score"].tolist() == [72.5, 81.0]
    assert history["source"].tolist() == ["first", "second"]


def test_missing_columns_are_rejected(tmp_path):
    store = AnalysisStore(tmp_path / "history.db")

    try:
        store.save_analysis(pd.DataFrame([{"company": "Alpha AG"}]))
    except ValueError as exc:
        assert "missing required columns" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


@pytest.mark.parametrize("invalid_score", [float("nan"), float("inf"), -1.0, 100.1, "not-a-number"])
def test_invalid_scores_are_not_persisted(tmp_path, invalid_score):
    store = AnalysisStore(tmp_path / "history.db")
    report = sample_report()
    report["attention_score"] = report["attention_score"].astype(object)
    report.loc[0, "attention_score"] = invalid_score

    with pytest.raises(ValueError, match="attention_score"):
        store.save_analysis(report)

    assert store.list_runs().empty


def test_empty_report_does_not_create_run(tmp_path):
    import pytest

    store = AnalysisStore(tmp_path / "history.db")
    empty_report = sample_report().iloc[0:0]
    with pytest.raises(ValueError, match="empty analysis report"):
        store.save_analysis(empty_report)
    assert store.list_runs().empty


@pytest.mark.parametrize("limit", [-1, 0, True, 1.5, "5"])
def test_list_runs_rejects_invalid_limit(tmp_path, limit):
    store = AnalysisStore(tmp_path / "history.db")
    store.save_analysis(sample_report())
    with pytest.raises(ValueError, match="positive integer"):
        store.list_runs(limit=limit)


def test_list_runs_respects_positive_limit(tmp_path):
    store = AnalysisStore(tmp_path / "history.db")
    store.save_analysis(sample_report(), source="first")
    store.save_analysis(sample_report(), source="second")
    runs = store.list_runs(limit=1)
    assert len(runs) == 1
    assert runs.iloc[0]["source"] == "second"


@pytest.mark.parametrize("column", ["company", "canton", "sector"])
@pytest.mark.parametrize("invalid", [None, "", "   "])
def test_history_rejects_missing_or_blank_labels(tmp_path, column, invalid):
    store = AnalysisStore(tmp_path / "history.db")
    report = sample_report()
    report.loc[0, column] = invalid
    with pytest.raises(ValueError, match=f"{column} must not be blank or missing"):
        store.save_analysis(report)
    assert store.list_runs().empty


@pytest.mark.parametrize("column", ["priority_band", "reasons"])
@pytest.mark.parametrize("invalid", [None, "", "   "])
def test_history_rejects_missing_priority_or_reasons(tmp_path, column, invalid):
    store = AnalysisStore(tmp_path / "history.db")
    report = sample_report()
    report.loc[0, column] = invalid
    with pytest.raises(ValueError, match=f"{column} must not be blank or missing"):
        store.save_analysis(report)
    assert store.list_runs().empty


@pytest.mark.parametrize("source", [None, "", "   ", 123])
def test_history_rejects_invalid_source(tmp_path, source):
    store = AnalysisStore(tmp_path / "history.db")
    with pytest.raises(ValueError, match="source must be a nonblank string"):
        store.save_analysis(sample_report(), source=source)
    assert store.list_runs().empty


def test_history_normalizes_source_whitespace(tmp_path):
    store = AnalysisStore(tmp_path / "history.db")
    store.save_analysis(sample_report(), source="  dashboard  ")
    assert store.list_runs().iloc[0]["source"] == "dashboard"


@pytest.mark.parametrize("company", [None, "", "   ", 123])
def test_company_history_rejects_invalid_lookup(tmp_path, company):
    store = AnalysisStore(tmp_path / "history.db")
    store.save_analysis(sample_report())
    with pytest.raises(ValueError, match="company must be a nonblank string"):
        store.company_history(company)


def test_company_history_trims_lookup_whitespace(tmp_path):
    store = AnalysisStore(tmp_path / "history.db")
    store.save_analysis(sample_report())
    history = store.company_history("  Alpha AG  ")
    assert history["company"].tolist() == ["Alpha AG"]


def test_history_normalizes_stored_labels_for_lookup(tmp_path):
    store = AnalysisStore(tmp_path / "history.db")
    report = sample_report()
    for column in ("company", "canton", "sector", "priority_band", "reasons"):
        report.loc[0, column] = f"  {report.loc[0, column]}  "
    store.save_analysis(report)
    history = store.company_history("Alpha AG")
    assert len(history) == 1
    assert history.iloc[0]["company"] == "Alpha AG"
    assert history.iloc[0]["canton"] == "ZH"
    assert history.iloc[0]["sector"] == "Technology"
    assert history.iloc[0]["priority_band"] == "high"
    assert history.iloc[0]["reasons"] == "elevated leverage"
