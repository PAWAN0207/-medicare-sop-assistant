import pytest
from fastapi.testclient import TestClient

from sopassist.api.app import create_app
from sopassist.errors import UpstreamError, UpstreamTimeout


@pytest.fixture
def client(service, settings):
    return TestClient(create_app(settings, service), raise_server_exceptions=False)


def test_ask_ok_shape_and_request_id(client):
    r = client.post("/v1/ask", json={"user_id": "U5001", "question": "What does Code Pink mean?"},
                    headers={"X-Request-ID": "abc123"})
    assert r.status_code == 200 and r.headers["X-Request-ID"] == "abc123"
    j = r.json()
    assert set(j) == {"answer", "refused", "reason", "citations", "cached", "index_generation", "request_id"}
    assert j["request_id"] == "abc123" and not j["refused"] and j["cached"] is False
    assert {"sop_id", "version", "title", "section", "section_title", "page"} == set(j["citations"][0])
    assert client.post("/v1/ask", json={"user_id": "U5001", "question": "What does Code Pink mean?"}).json()["cached"]


def test_error_envelope_unknown_user(client):
    r = client.post("/v1/ask", json={"user_id": "nope", "question": "hi"})
    assert r.status_code == 403
    e = r.json()["error"]
    assert e["code"] == "UNKNOWN_USER" and e["request_id"] and "details" in e


def test_validation_error_envelope(client):
    r = client.post("/v1/ask", json={"user_id": "U1001"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_REQUEST"
    assert client.post("/v1/ask", json={"user_id": "U1001", "question": "x" * 1001}).status_code == 422


def test_pii_blocked_422_without_echo(client):
    q = "My patient's Aadhaar is 4521 8890 1234, can I store a copy?"
    r = client.post("/v1/ask", json={"user_id": "U1001", "question": q})
    assert r.status_code == 422
    body = r.text
    assert r.json()["error"]["code"] == "PATIENT_DATA_DETECTED" and "4521" not in body
    assert r.json()["error"]["details"]["types"] == ["aadhaar_number"]


@pytest.mark.parametrize("exc,status,code", [(UpstreamTimeout("t"), 504, "UPSTREAM_TIMEOUT"),
                                              (UpstreamError("u"), 502, "UPSTREAM_ERROR"),
                                              (RuntimeError("boom"), 500, "INTERNAL")])
def test_upstream_failures_map_to_clean_errors(client, service, exc, status, code):
    class Bad:
        model_id = "bad"
        def generate(self, s, u): raise exc
    service.llm = Bad()
    r = client.post("/v1/ask", json={"user_id": "U5001", "question": "What does Code Pink mean?"})
    assert r.status_code == status and r.json()["error"]["code"] == code
    assert "boom" not in r.text                                   # internals not leaked
    assert service.store.cache_size() == 0                        # failures are never cached


def test_healthz(client):
    j = client.get("/healthz").json()
    assert j["status"] == "ok" and j["documents"] == 15
