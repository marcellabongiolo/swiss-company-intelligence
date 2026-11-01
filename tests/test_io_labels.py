import pytest

from swiss_company_intel.io import load_companies


@pytest.mark.parametrize("field", ["company", "sector"])
@pytest.mark.parametrize("value", ["", "   "])
def test_import_rejects_blank_required_labels(tmp_path, field, value):
    columns = [
        "company", "canton", "sector", "revenue_m_chf", "revenue_growth_pct",
        "ebitda_margin_pct", "debt_to_equity", "current_ratio",
        "employee_growth_pct", "customer_concentration_pct", "late_payment_pct",
    ]
    row = dict(zip(columns, ["Example AG", "ZH", "Software", "10", "5", "15", "1", "2", "3", "10", "5"]))
    row[field] = value
    csv_file = tmp_path / "companies.csv"
    csv_file.write_text(",".join(columns) + "\\n" + ",".join(row[column] for column in columns) + "\\n", encoding="utf-8")
    with pytest.raises(ValueError, match=field):
        load_companies(csv_file)
