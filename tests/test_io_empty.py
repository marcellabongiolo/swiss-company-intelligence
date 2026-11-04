import pytest

from swiss_company_intel.io import load_companies


def test_header_only_csv_is_rejected(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text(
        "company,canton,sector,revenue_m_chf,revenue_growth_pct,"
        "ebitda_margin_pct,debt_to_equity,current_ratio,employee_growth_pct,"
        "customer_concentration_pct,late_payment_pct\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="dataset is empty"):
        load_companies(path)


def test_in_memory_validation_matches_file_validation_and_does_not_mutate(tmp_path):
    import pandas as pd
    from swiss_company_intel.io import validate_companies

    raw = pd.DataFrame([{
        " Company ": " Alpha AG ", "CANTON": "zh", "sector": " Software ",
        "revenue_m_chf": 100.0, "revenue_growth_pct": 4.0,
        "ebitda_margin_pct": 15.0, "debt_to_equity": 0.8,
        "current_ratio": 1.8, "employee_growth_pct": 3.0,
        "customer_concentration_pct": 15.0, "late_payment_pct": 8.0,
    }])
    original = raw.copy(deep=True)
    path = tmp_path / "companies.csv"
    raw.to_csv(path, index=False)
    expected = load_companies(path)
    actual = validate_companies(raw)
    pd.testing.assert_frame_equal(actual, expected)
    pd.testing.assert_frame_equal(raw, original)


def test_in_memory_validation_rejects_invalid_upload():
    import pandas as pd
    from swiss_company_intel.io import validate_companies

    with pytest.raises(ValueError, match="Missing required columns"):
        validate_companies(pd.DataFrame({"company": ["Alpha AG"]}))
