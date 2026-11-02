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
