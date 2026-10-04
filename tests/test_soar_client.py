from soar_monthly_incident_report.soar_client import SoarClient


class FakeRest:
    def __init__(self, incidents, field=None, query_result=None, workflows=None):
        self.incidents = incidents
        self.field = field or {}
        self.query_result = query_result or []
        self.workflow_response = {"entities": workflows or []}
        self.paged_calls = []

    def post(self, uri, payload):
        if uri.startswith("/incidents/query_paged"):
            self.paged_calls.append(payload)
            start, length = payload["start"], payload["length"]
            return {"data": self.incidents[start : start + length]}
        self.last_query = payload
        return self.query_result

    def get(self, uri):
        if uri.startswith("/types/incident/fields/"):
            return self.field
        if uri == "/workflows":
            return self.workflow_response
        raise AssertionError(f"unexpected GET {uri}")


def test_paging_stops_at_cutoff():
    incidents = [{"id": i, "create_date": 1000 - i * 10} for i in range(25)]
    rest = FakeRest(incidents)
    result = SoarClient(rest, page_size=10).closed_incidents_since(cutoff_ms=845)
    assert [i["id"] for i in result] == list(range(16))
    assert len(rest.paged_calls) == 2
    assert rest.paged_calls[1]["start"] == 10


def test_paging_stops_on_short_page():
    rest = FakeRest([{"id": 1, "create_date": 100}])
    assert len(SoarClient(rest, page_size=10).closed_incidents_since(0)) == 1
    assert len(rest.paged_calls) == 1


def test_field_values_and_property_query():
    rest = FakeRest(
        [], field={"values": [{"value": 1, "label": "Blocked"}]}, query_result=[{"id": 9}]
    )
    client = SoarClient(rest)
    assert client.field_values("action_info") == [{"value": 1, "label": "Blocked"}]
    assert client.incidents_where("second_info", "Ok") == [{"id": 9}]
    condition = rest.last_query["filters"][0]["conditions"][0]
    assert condition == {"field_name": "properties.second_info", "method": "equals", "value": "Ok"}


def test_workflows():
    rest = FakeRest([], workflows=[{"workflow_id": 1}])
    assert SoarClient(rest).workflows() == [{"workflow_id": 1}]
