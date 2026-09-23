import pandas as pd

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
