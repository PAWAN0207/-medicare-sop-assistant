import httpx
import pytest

from sopassist.adapters import openai_compat as oc
from sopassist.errors import UpstreamError, UpstreamTimeout


def _resp(status, body=None):
    return httpx.Response(status, json=body or {}, request=httpx.Request("POST", "http://x"))


OK = {"choices": [{"message": {"content": "hi"}}], "usage": {"prompt_tokens": 3, "completion_tokens": 1}}


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(oc.time, "sleep", lambda s: None)


def llm():
    return oc.OpenAICompatLLM("http://x", "k", "m", timeout_s=1, max_retries=2)


def test_retries_5xx_then_succeeds(monkeypatch):
    calls = iter([_resp(503), _resp(429), _resp(200, OK)])
    n = []
    monkeypatch.setattr(oc.httpx, "post", lambda *a, **k: (n.append(1), next(calls))[1])
    r = llm().generate("s", "u")
    assert r.text == "hi" and (r.tokens_in, r.tokens_out) == (3, 1) and len(n) == 3


def test_4xx_not_retried(monkeypatch):
    n = []
    monkeypatch.setattr(oc.httpx, "post", lambda *a, **k: (n.append(1), _resp(401))[1])
    with pytest.raises(UpstreamError):
        llm().generate("s", "u")
    assert len(n) == 1


def test_timeout_after_retries(monkeypatch):
    def raise_timeout(*a, **k):
        raise httpx.ReadTimeout("t")
    monkeypatch.setattr(oc.httpx, "post", raise_timeout)
    with pytest.raises(UpstreamTimeout):
        llm().generate("s", "u")


def test_timeout_is_passed_to_every_call(monkeypatch):
    seen = {}
    monkeypatch.setattr(oc.httpx, "post", lambda *a, **k: (seen.update(k), _resp(200, OK))[1])
    llm().generate("s", "u")
    assert seen["timeout"] == 1


def test_malformed_response(monkeypatch):
    monkeypatch.setattr(oc.httpx, "post", lambda *a, **k: _resp(200, {"nope": 1}))
    with pytest.raises(UpstreamError):
        llm().generate("s", "u")


def test_embedder_batches_and_orders(monkeypatch):
    def post(url, json, **k):
        return _resp(200, {"data": [{"index": i, "embedding": [float(len(t))]} for i, t in reversed(list(enumerate(json["input"])))]})
    monkeypatch.setattr(oc.httpx, "post", post)
    e = oc.OpenAICompatEmbedder("http://x", "k", "m")
    out = e.embed(["a" * i for i in range(1, 121)])
    assert [v[0] for v in out] == list(range(1, 121))
