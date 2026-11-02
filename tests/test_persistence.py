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
