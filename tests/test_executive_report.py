import pandas as pd
import pytest

from swiss_company_intel.executive_report import executive_report_html


def test_report_contains_summary_and_escapes_uploaded_text():
    frame = pd.DataFrame([{
        "company": "<script>alert(1)</script>",
        "sector": "Technology",
        "canton": "ZH",
        "attention_score": 82.5,
        "priority_band": "critical",
        "reasons": 'alert & "review"',
    }])
    html = executive_report_html(frame).decode("utf-8")
    assert "&lt;script&gt;" in html
    assert "<script>" not in html
    assert "alert &amp; &quot;review&quot;" in html
    assert "82.5" in html
    assert "dados sintéticos" in html
    assert "Salvar como PDF" in html


def test_empty_report_is_rejected():
    with pytest.raises(ValueError, match="empty"):
        executive_report_html(pd.DataFrame(columns=[
            "company", "sector", "canton", "attention_score", "priority_band", "reasons"
        ]))


def test_missing_columns_are_rejected():
    with pytest.raises(ValueError, match="Missing report columns"):
        executive_report_html(pd.DataFrame([{"company": "Demo"}]))
