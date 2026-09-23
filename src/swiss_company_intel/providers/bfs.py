from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
    """Small client for the Swiss Federal Statistical Office PxWeb API.

    The client intentionally keeps transport logic separate from the scoring
    engine so external data can be swapped, cached or mocked without changing
    the analysis code.
    """

    BASE_URL = "https://www.pxweb.bfs.admin.ch/api/v1/en"

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 15.0,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()

    def _url(self, cube_path: str) -> str:
        return f"{self.base_url}/{cube_path.lstrip('/')}"

    def get_metadata(self, cube: BFSCube = ENTERPRISE_STATISTICS) -> dict[str, Any]:
        """Return official metadata for a STAT-TAB cube."""
        response = self.session.get(self._url(cube.path), timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Unexpected BFS metadata response")
        return payload

    def query(
        self,
        selections: dict[str, list[str]],
        cube: BFSCube = ENTERPRISE_STATISTICS,
        response_format: str = "json-stat2",
    ) -> dict[str, Any]:
        """Query a cube using PxWeb variable codes and value codes.

        `selections` maps variable codes from `get_metadata()` to the selected
        value codes, which avoids hard-coding labels that can change by language.
        """
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
            raise ValueError("Unexpected BFS query response")
        return payload

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
