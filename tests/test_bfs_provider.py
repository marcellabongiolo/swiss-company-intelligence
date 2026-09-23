from swiss_company_intel.providers.bfs import BFSClient, ENTERPRISE_STATISTICS


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

    def get(self, url, timeout):
        self.last_get = (url, timeout)
        return FakeResponse(
            {
                "title": "Enterprise statistics",
                "variables": [
                    {
                        "code": "Year",
                        "text": "Year",
                        "values": ["2023", "2024"],
                        "valueTexts": ["2023", "2024"],
                    }
                ],
            }
        )

    def post(self, url, json, timeout):
        self.last_post = (url, json, timeout)
        return FakeResponse({"class": "dataset", "value": [1, 2]})


def test_metadata_and_variable_summary():
    session = FakeSession()
    client = BFSClient(session=session)
    metadata = client.get_metadata()

    assert ENTERPRISE_STATISTICS.path in session.last_get[0]
    summary = client.variable_summary(metadata)
    assert summary[0]["code"] == "Year"
    assert summary[0]["value_count"] == 2


def test_query_builds_pxweb_payload():
    session = FakeSession()
    client = BFSClient(session=session)
    result = client.query({"Year": ["2024"]})

    assert result["class"] == "dataset"
    payload = session.last_post[1]
    assert payload["query"][0]["code"] == "Year"
    assert payload["query"][0]["selection"]["values"] == ["2024"]
