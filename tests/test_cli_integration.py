from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from swiss_company_intel.cli import app


runner = CliRunner()


def write_sample_csv(path: Path) -> None:
    pd.DataFrame(
        [
            {
                "company": "Stable AG",
                "canton": "ZH",
                "sector": "Technology",
                "revenue_m_chf": 100.0,
                "revenue_growth_pct": 4.0,
                "ebitda_margin_pct": 15.0,
                "debt_to_equity": 0.5,
                "current_ratio": 1.8,
                "employee_growth_pct": 3.0,
                "customer_concentration_pct": 15.0,
                "late_payment_pct": 8.0,
            },
            {
                "company": "Watch AG",
                "canton": "ZH",
                "sector": "Technology",
                "revenue_m_chf": 80.0,
                "revenue_growth_pct": -12.0,
                "ebitda_margin_pct": 6.0,
                "debt_to_equity": 3.0,
                "current_ratio": 0.8,
                "employee_growth_pct": -8.0,
                "customer_concentration_pct": 50.0,
                "late_payment_pct": 30.0,
            },
        ]
    ).to_csv(path, index=False)


def test_cli_analyze_happy_path(tmp_path):
    input_file = tmp_path / "companies.csv"
    output_file = tmp_path / "report.csv"
    write_sample_csv(input_file)

    result = runner.invoke(
        app,
        [
            "analyze",
            str(input_file),
            "--output",
            str(output_file),
            "--top",
            "1",
        ],
    )

    assert result.exit_code == 0
    assert output_file.exists()
    report = pd.read_csv(output_file)
    assert report.iloc[0]["company"] == "Watch AG"
    assert "Report written to:" in result.stdout


def test_cli_analyze_invalid_input_returns_nonzero_exit(tmp_path):
    missing_file = tmp_path / "missing.csv"

    result = runner.invoke(app, ["analyze", str(missing_file)])

    assert result.exit_code == 1
    assert "Error:" in result.stdout
    assert "Input file not found" in result.stdout
