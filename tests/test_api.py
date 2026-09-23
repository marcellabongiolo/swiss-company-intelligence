from fastapi.testclient import TestClient

from swiss_company_intel.api import app


client = TestClient(app)


def company(name: str, canton: str, sector: str, debt: float) -> dict:
    return {
        "company": name,
        "canton": canton,
        "sector": sector,
        "revenue_m_chf": 100.0,
        "revenue_growth_pct": 4.0,
        "ebitda_margin_pct": 15.0,
        "debt_to_equity": debt,
        "current_ratio": 1.8,
        "employee_growth_pct": 3.0,
        "customer_concentration_pct": 15.0,
        "late_payment_pct": 8.0,
    }


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_score_endpoint_returns_explainable_score():
    response = client.post(
        "/score",
        json={
            "debt_to_equity": 3.0,
            "current_ratio": 1.8,
            "customer_concentration_pct": 15.0,
            "late_payment_pct": 8.0,
            "revenue_growth_pct": 4.0,
            "employee_growth_pct": 3.0,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["attention_score"] == 18.0
    assert "elevated leverage (3.00x D/E)" in payload["reasons"]


def test_analyze_endpoint_ranks_portfolio():
    response = client.post(
        "/analyze",
        json={
            "companies": [
                company("Stable AG", "ZH", "Technology", 0.5),
                company("Watch AG", "ZH", "Technology", 3.0),
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["company"] == "Watch AG"
    assert payload[0]["attention_score"] > payload[1]["attention_score"]


def test_invalid_canton_returns_422():
    response = client.post(
        "/analyze",
        json={"companies": [company("Invalid AG", "XX", "Technology", 1.0)]},
    )

    assert response.status_code == 422
