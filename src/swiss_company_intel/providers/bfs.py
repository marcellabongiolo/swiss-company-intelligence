from __future__ import annotations

import itertools
import json
import time
from dataclasses import dataclass
from typing import Any

import pandas as pd
import requests


@dataclass(frozen=True)
class BFSCube:
    """A known Federal Statistical Office STAT-TAB data cube."""

    name: str
    path: str
    description: str


ENTERPRISE_STATISTICS = BFSCube(
    name="enterprise_statistics",
    path="px-x-0606010000_102/px-x-0606010000_102/px-x-0606010000_102.px",
    description=(
        "FSO enterprise and employment statistics by economic activity, "
        "enterprise-size group and group type."
    ),
)


class BFSClient:
    """Client for the Swiss Federal Statistical Office PxWeb API."""

    BASE_URL = "https://www.pxweb.bfs.admin.ch/api/v1/en"

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 15.0,
        session: requests.Session | None = None,
        cache_ttl: float = 900.0,
    ) -> None:
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def _url(self, cube_path: str) -> str:
        return f"{self.base_url}/{cube_path.lstrip('/')}"

    def _cache_key(
        self,
        cube: BFSCube,
        selections: dict[str, list[str]],
        response_format: str,
    ) -> str:
        return json.dumps(
            {
                "cube": cube.path,
                "selections": selections,
                "format": response_format,
            },
            sort_keys=True,
        )

    def get_metadata(self, cube: BFSCube = ENTERPRISE_STATISTICS) -> dict[str, Any]:
        """Return official metadata for a STAT-TAB cube."""
        response = self.session.get(self._url(cube.path), timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise TypeError("Unexpected BFS metadata response")
        return payload

    def query(
        self,
        selections: dict[str, list[str]],
        cube: BFSCube = ENTERPRISE_STATISTICS,
        response_format: str = "json-stat2",
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Query a cube using PxWeb variable codes and value codes."""
        key = self._cache_key(cube, selections, response_format)
        if use_cache and key in self._cache:
            created_at, cached = self._cache[key]
            if time.monotonic() - created_at < self.cache_ttl:
                return cached
            del self._cache[key]

        query = [
            {
                "code": variable,
                "selection": {"filter": "item", "values": values},
            }
            for variable, values in selections.items()
        ]
        response = self.session.post(
            self._url(cube.path),
            json={"query": query, "response": {"format": response_format}},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise TypeError("Unexpected BFS query response")

        if use_cache:
            self._cache[key] = (time.monotonic(), payload)
        return payload

    def latest_enterprise_statistics(
        self,
        cube: BFSCube = ENTERPRISE_STATISTICS,
    ) -> pd.DataFrame:
        """Fetch a small reproducible subset of the latest official enterprise data.

        The method reads metadata first, selects the latest value of the time
        dimension and the first available value for the observation-unit
        dimension, while keeping all values for the remaining dimensions.
        """
        metadata = self.get_metadata(cube)
        variables = metadata.get("variables", [])
        if not isinstance(variables, list) or not variables:
            raise ValueError("BFS metadata does not contain variables")

        selections: dict[str, list[str]] = {}
        for index, variable in enumerate(variables):
            code = str(variable.get("code", ""))
            values = [str(value) for value in variable.get("values", [])]
            if not code or not values:
                raise ValueError("BFS variable metadata is incomplete")

            is_time = bool(variable.get("time"))
            if is_time:
                selections[code] = [values[-1]]
            elif index == 0:
                selections[code] = [values[0]]
            else:
                selections[code] = values

        payload = self.query(selections, cube=cube)
        frame = self.jsonstat2_to_dataframe(payload)
        frame.attrs["source"] = "Swiss Federal Statistical Office (FSO/BFS) STAT-TAB"
        frame.attrs["cube"] = cube.name
        frame.attrs["cube_path"] = cube.path
        return frame

    @staticmethod
    def jsonstat2_to_dataframe(payload: dict[str, Any]) -> pd.DataFrame:
        """Convert a JSON-stat2 dataset payload into a tidy DataFrame."""
        dimension_ids = payload.get("id")
        sizes = payload.get("size")
        dimensions = payload.get("dimension")
        values = payload.get("value")

        if not isinstance(dimension_ids, list) or not isinstance(sizes, list):
            raise ValueError("Invalid JSON-stat2 dimensions")
        if not isinstance(dimensions, dict):
            raise ValueError("Invalid JSON-stat2 dimension metadata")
        if not isinstance(values, list):
            raise ValueError("Invalid JSON-stat2 values")
        if len(dimension_ids) != len(sizes):
            raise ValueError("JSON-stat2 id and size lengths differ")

        categories: list[list[tuple[str, str]]] = []
        for dimension_id in dimension_ids:
            dimension = dimensions.get(dimension_id, {})
            category = dimension.get("category", {})
            index = category.get("index", {})
            labels = category.get("label", {})

            if isinstance(index, dict):
                ordered_codes = [
                    code for code, _ in sorted(index.items(), key=lambda item: item[1])
                ]
            elif isinstance(index, list):
                ordered_codes = [str(code) for code in index]
            else:
                raise ValueError(f"Invalid category index for {dimension_id}")

            categories.append(
                [(str(code), str(labels.get(code, code))) for code in ordered_codes]
            )

        expected = 1
        for size in sizes:
            expected *= int(size)
        if expected != len(values):
            raise ValueError(
                f"JSON-stat2 value count mismatch: expected {expected}, got {len(values)}"
            )

        rows: list[dict[str, Any]] = []
        for position, combination in enumerate(itertools.product(*categories)):
            row: dict[str, Any] = {}
            for dimension_id, (code, label) in zip(
                dimension_ids,
                combination,
                strict=True,
            ):
                row[str(dimension_id)] = code
                row[f"{dimension_id}_label"] = label
            row["value"] = values[position]
            rows.append(row)

        return pd.DataFrame(rows)

    @staticmethod
    def variable_summary(metadata: dict[str, Any]) -> list[dict[str, Any]]:
        """Flatten PxWeb variable metadata for display in the dashboard."""
        variables = metadata.get("variables", [])
        summary: list[dict[str, Any]] = []
        for variable in variables:
            values = variable.get("values", [])
            value_texts = variable.get("valueTexts", [])
            summary.append(
                {
                    "code": variable.get("code", ""),
                    "label": variable.get("text", ""),
                    "value_count": len(values),
                    "sample_values": ", ".join(map(str, value_texts[:5])),
                }
            )
        return summary
