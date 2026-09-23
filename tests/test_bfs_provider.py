from swiss_company_intel.providers.bfs import ENTERPRISE_STATISTICS, BFSClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self):
        self.last_get = None
        self.last_post = None
        self.post_count = 0

    def get(self, url, timeout):
        self.last_get = (url, timeout)
        return FakeResponse(
            {
                "title": "Enterprise statistics",
                "variables": [
                    {
                        "code": "Unit",
                        "text": "Observation unit",
                        "values": ["enterprise", "employment"],
                        "valueTexts": ["Enterprise", "Employment"],
                    },
                    {
                        "code": "Sector",
                        "text": "Economic activity",
                        "values": ["total", "tech"],
                        "valueTexts": ["Total", "Technology"],
                    },
                    {
                        "code": "Year",
                        "text": "Year",
                        "values": ["2023", "2024"],
                        "valueTexts": ["2023", "2024"],
                        "time": True,
                    },
                ],
            }
        )

    def post(self, url, json, timeout):
        self.last_post = (url, json, timeout)
        self.post_count += 1
        return FakeResponse(
            {
                "class": "dataset",
                "id": ["Unit", "Sector", "Year"],
                "size": [1, 2, 1],
                "dimension": {
                    "Unit": {
                        "category": {
                            "index": {"enterprise": 0},
                            "label": {"enterprise": "Enterprise"},
                        }
                    },
                    "Sector": {
                        "category": {
                            "index": {"total": 0, "tech": 1},
                            "label": {"total": "Total", "tech": "Technology"},
                        }
                    },
                    "Year": {
                        "category": {
                            "index": {"2024": 0},
                            "label": {"2024": "2024"},
                        }
                    },
                },
                "value": [100, 25],
            }
        )


def test_metadata_and_variable_summary():
    session = FakeSession()
    client = BFSClient(session=session)
    metadata = client.get_metadata()

    assert ENTERPRISE_STATISTICS.path in session.last_get[0]
    summary = client.variable_summary(metadata)
    assert summary[0]["code"] == "Unit"
    assert summary[0]["value_count"] == 2


def test_query_builds_pxweb_payload():
    session = FakeSession()
    client = BFSClient(session=session)
    result = client.query({"Year": ["2024"]})

    assert result["class"] == "dataset"
    payload = session.last_post[1]
    assert payload["query"][0]["code"] == "Year"
    assert payload["query"][0]["selection"]["values"] == ["2024"]


def test_query_uses_cache():
    session = FakeSession()
    client = BFSClient(session=session, cache_ttl=60)

    client.query({"Year": ["2024"]})
    client.query({"Year": ["2024"]})

    assert session.post_count == 1


def test_jsonstat2_to_dataframe():
    session = FakeSession()
    client = BFSClient(session=session)
    payload = session.post("unused", {}, 1).json()

    frame = client.jsonstat2_to_dataframe(payload)

    assert frame.shape == (2, 7)
    assert frame["Sector_label"].tolist() == ["Total", "Technology"]
    assert frame["value"].tolist() == [100, 25]


def test_latest_enterprise_statistics_selects_latest_year_and_returns_dataframe():
    session = FakeSession()
    client = BFSClient(session=session)

    frame = client.latest_enterprise_statistics()

    request = session.last_post[1]["query"]
    selections = {
        item["code"]: item["selection"]["values"]
        for item in request
    }

    assert selections["Unit"] == ["enterprise"]
    assert selections["Sector"] == ["total", "tech"]
    assert selections["Year"] == ["2024"]
    assert frame["Year"].unique().tolist() == ["2024"]
    assert frame.attrs["source"].startswith("Swiss Federal Statistical Office")
