import json
import lowcap_short_system.live.http_transport as ht


class _FakeResp:
    def __init__(self, body: bytes) -> None:
        self._body = body
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False
    def read(self) -> bytes:
        return self._body


def test_serializes_payload_and_parses_response(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["data"] = req.data
        captured["ctype"] = req.headers.get("Content-type")
        return _FakeResp(b'{"ok": true, "shares": 500}')

    monkeypatch.setattr(ht.urllib.request, "urlopen", fake_urlopen)
    out = ht.HttpTransport().request("POST", "https://api.example/orders", {"Authorization": "Bearer z"}, {"a": 1})
    assert out == {"ok": True, "shares": 500}
    assert captured["method"] == "POST"
    assert json.loads(captured["data"]) == {"a": 1}
    assert captured["ctype"] == "application/json"


def test_empty_body_returns_empty_dict(monkeypatch):
    monkeypatch.setattr(ht.urllib.request, "urlopen", lambda req, timeout=None: _FakeResp(b""))
    assert ht.HttpTransport().request("GET", "https://api.example/ping", {}, None) == {}
