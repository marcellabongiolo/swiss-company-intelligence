import json

import pandas as pd
import pytest

from swiss_company_intel.config import load_score_weights, score_weights_from_mapping
from swiss_company_intel.models import ScoreWeights
from swiss_company_intel.scoring import score_row


DEFAULT_WEIGHTS = {
    "leverage": 18,
    "liquidity": 16,
    "concentration": 18,
    "late_payment": 14,
    "revenue_decline": 12,
    "employee_decline": 8,
    "anomaly": 14,
}


def test_load_score_weights_from_json(tmp_path):
    path = tmp_path / "weights.json"
    path.write_text(json.dumps(DEFAULT_WEIGHTS), encoding="utf-8")

    weights = load_score_weights(path)

    assert weights == ScoreWeights()


def test_weights_must_add_up_to_100():
    values = DEFAULT_WEIGHTS | {"anomaly": 10}

    with pytest.raises(ValueError, match="add up to 100"):
        score_weights_from_mapping(values)


def test_weights_reject_unknown_fields():
    values = DEFAULT_WEIGHTS | {"mystery": 1}

    with pytest.raises(ValueError, match="Unknown score weight"):
        score_weights_from_mapping(values)


def test_custom_weights_change_score():
    row = pd.Series(
        {
            "debt_to_equity": 3.0,
            "current_ratio": 1.8,
            "customer_concentration_pct": 15.0,
            "late_payment_pct": 8.0,
            "revenue_growth_pct": 4.0,
            "employee_growth_pct": 3.0,
            "sector_anomaly_strength": 0.0,
        }
    )

    default_score, _ = score_row(row)
    leverage_focused = score_weights_from_mapping(
        {
            "leverage": 100,
            "liquidity": 0,
            "concentration": 0,
            "late_payment": 0,
            "revenue_decline": 0,
            "employee_decline": 0,
            "anomaly": 0,
        }
    )
    custom_score, _ = score_row(row, leverage_focused)

    assert default_score == 18.0
    assert custom_score == 100.0
