import pytest

from swiss_company_intel.io import load_companies


def test_import_rejects_duplicate_normalized_columns(tmp_path):
    csv_file = tmp_path / "companies.csv"
    csv_file.write_text(
        "company, Company ,canton,sector,revenue_m_chf,revenue_growth_pct,"
        "ebitda_margin_pct,debt_to_equity,current_ratio,employee_growth_pct,"
        "customer_concentration_pct,late_payment_pct\\n"
        "Example AG,Duplicate AG,ZH,Software,10,5,15,1,2,3,10,5\\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate CSV column"):
        load_companies(csv_file)
