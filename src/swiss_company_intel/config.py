from __future__ import annotations

import json
import math
from dataclasses import fields
from pathlib import Path
from typing import Any

from .models import ScoreWeights


WEIGHT_NAMES = tuple(field.name for field in fields(ScoreWeights))


def score_weights_from_mapping(values: dict[str, Any]) -> ScoreWeights:
    """Build and validate ScoreWeights from a dictionary."""
    unknown = sorted(set(values) - set(WEIGHT_NAMES))
    if unknown:
        raise ValueError(f"Unknown score weight(s): {', '.join(unknown)}")

    missing = sorted(set(WEIGHT_NAMES) - set(values))
    if missing:
        raise ValueError(f"Missing score weight(s): {', '.join(missing)}")

    try:
        normalized = {name: float(values[name]) for name in WEIGHT_NAMES}
    except (TypeError, ValueError) as exc:
        raise ValueError("All score weights must be numeric") from exc

    negative = [name for name, value in normalized.items() if value < 0]
    if negative:
        raise ValueError(f"Score weights cannot be negative: {', '.join(negative)}")

    weights = ScoreWeights(**normalized)
    if not math.isclose(weights.total(), 100.0, abs_tol=1e-9):
        raise ValueError(f"Score weights must add up to 100, got {weights.total():.2f}")

    return weights


def load_score_weights(path: str | Path) -> ScoreWeights:
    """Load score weights from a JSON configuration file."""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Score weights file not found: {config_path}")

    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in score weights file: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise ValueError("Score weights configuration must be a JSON object")

    return score_weights_from_mapping(payload)
