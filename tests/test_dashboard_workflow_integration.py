"""End-to-end coverage for the dashboard's data workflow without a browser."""

from io import BytesIO

import pandas as pd

from swiss_company_intel.analyzer import CompanyAnalyzer
from swiss_company_intel.dashboard_logic import filter_report, report_to_csv_bytes
from swiss_company_intel.io import load_companies
from swiss_company_intel.persistence import AnalysisStore


def test_dashboard_pipeline_filters_exports_and_preserves_historical_snapshot(tmp_path):
    source = tmp_path / "companies.csv"
    pd.DataFrame([
        {
            "company": "Stable AG", "canton": "ZH", "sector": "Technology",
            "revenue_m_chf": 100, "revenue_growth_pct": 5,
            "ebitda_margin_pct": 20, "debt_to_equity": 0.4,
            "current_ratio": 2.0, "employee_growth_pct": 4,
            "customer_concentration_pct": 10, "late_payment_pct": 4,
        },
        {
            "company": "Watch AG", "canton": "ZG", "sector": "Technology",
            "revenue_m_chf": 80, "revenue_growth_pct": -18,
            "ebitda_margin_pct": 3, "debt_to_equity": 3.1,
            "current_ratio": 0.7, "employee_growth_pct": -12,
            "customer_concentration_pct": 65, "late_payment_pct": 35,
        },
    ]).to_csv(source, index=False)

    report = CompanyAnalyzer().report_columns(CompanyAnalyzer().analyze(load_companies(source)))
    filtered = filter_report(report, company_query="watch", cantons=["ZG"], min_attention_score=0)
    assert filtered["company"].tolist() == ["Watch AG"]

    downloaded = pd.read_csv(BytesIO(report_to_csv_bytes(filtered)))
    pd.testing.assert_frame_equal(downloaded, filtered)

    store = AnalysisStore(tmp_path / "history.db")
    run_id = store.save_analysis(report, source="integration")
    snapshot = store.run_details(run_id)
    assert set(snapshot["company"]) == {"Stable AG", "Watch AG"}
    assert store.list_runs().iloc[0]["company_count"] == 2

    historical_export = pd.read_csv(BytesIO(report_to_csv_bytes(snapshot)))
    pd.testing.assert_frame_equal(historical_export, snapshot)
    assert store.company_history("Watch AG").iloc[0]["run_id"] == run_id
