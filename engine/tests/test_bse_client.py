import httpx
import pytest
from engine.bse_client import BSEClient
from engine.errors import BSEUnavailableError


def _client(handler):
    return BSEClient(transport=httpx.MockTransport(handler), rate_delay=0)


def test_get_json_sends_browser_headers_and_returns_table():
    def handler(req):
        assert "Mozilla" in req.headers["user-agent"]
        assert req.headers["referer"] == "https://www.bseindia.com/"
        return httpx.Response(200, json={"Table": [{"NEWSID": "abc"}]})
    data = _client(handler).get_json("https://api.bseindia.com/x", {"q": "1"})
    assert data["Table"][0]["NEWSID"] == "abc"


def test_get_json_raises_friendly_on_5xx():
    handler = lambda req: httpx.Response(503)
    with pytest.raises(BSEUnavailableError):
        _client(handler).get_json("https://api.bseindia.com/x", {})


def test_get_json_raises_friendly_on_transport_error():
    def handler(req):
        raise httpx.ConnectError("boom")
    with pytest.raises(BSEUnavailableError):
        _client(handler).get_json("https://api.bseindia.com/x", {})


def test_get_bytes_returns_content():
    handler = lambda req: httpx.Response(200, content=b"%PDF-1.7 ...")
    assert _client(handler).get_bytes("https://www.bseindia.com/f.pdf").startswith(b"%PDF-")


def test_get_text_returns_body():
    handler = lambda req: httpx.Response(200, text="<li>hi</li>")
    assert "<li>" in _client(handler).get_text("https://api.bseindia.com/s", {"text": "x"})
