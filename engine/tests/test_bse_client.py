import httpx
import pytest
from engine.bse_client import BSEClient
from engine.errors import BSEUnavailableError


def _client(handler):
    return BSEClient(transport=httpx.MockTransport(handler), rate_delay=0, retry_backoff=0)


def test_get_json_sends_browser_headers_and_returns_table():
    def handler(req):
        assert req.headers["referer"] == "https://www.bseindia.com/"
        return httpx.Response(200, json={"Table": [{"NEWSID": "abc"}]})
    data = _client(handler).get_json("https://api.bseindia.com/x", {"q": "1"})
    assert data["Table"][0]["NEWSID"] == "abc"


def test_sends_the_bse_origin_and_fetch_context():
    seen = {}

    def handler(req):
        seen.update(req.headers)
        return httpx.Response(200, json={"Table": []})
    _client(handler).get_json("https://api.bseindia.com/x", {})
    assert seen["origin"] == "https://www.bseindia.com"
    assert seen["accept-language"].startswith("en")
    assert (seen["sec-fetch-mode"], seen["sec-fetch-site"], seen["sec-fetch-dest"]) == \
        ("cors", "same-site", "empty")
    assert "gzip" in seen["accept-encoding"]


def test_custom_ca_file_is_the_effective_trust_store(tmp_path, monkeypatch):
    import certifi
    from curl_cffi import requests as curl_requests
    bundle = tmp_path / "custom-ca.pem"
    from pathlib import Path
    bundle.write_bytes(Path(certifi.where()).read_bytes())
    monkeypatch.setenv("SSL_CERT_FILE", str(bundle))
    monkeypatch.setenv("SSL_CERT_DIR", str(tmp_path))
    client = BSEClient()
    try:
        assert isinstance(client._client, curl_requests.Session)
        assert client._client.verify == str(bundle)
        assert not client._client.curl_options
    finally:
        client.close()


def test_custom_ca_directory_does_not_add_certifi_roots(tmp_path, monkeypatch):
    from curl_cffi import CurlOpt, ffi, requests as curl_requests
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.setenv("SSL_CERT_DIR", str(tmp_path))
    client = BSEClient()
    try:
        assert isinstance(client._client, curl_requests.Session)
        assert client._client.verify is not False
        assert client._client.curl_options[CurlOpt.CAPATH] == str(tmp_path)
        assert client._client.curl_options[CurlOpt.CAINFO] == ffi.NULL
    finally:
        client.close()


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


def test_get_text_raises_friendly_on_4xx():
    handler = lambda req: httpx.Response(404, text="<html>not found</html>")
    with pytest.raises(BSEUnavailableError):
        _client(handler).get_text("https://api.bseindia.com/s", {"text": "x"})


def test_get_json_raises_friendly_on_4xx():
    handler = lambda req: httpx.Response(404, json={"oops": True})
    with pytest.raises(BSEUnavailableError):
        _client(handler).get_json("https://api.bseindia.com/x", {})


def test_get_bytes_raises_friendly_on_5xx():
    handler = lambda req: httpx.Response(503, content=b"down")
    with pytest.raises(BSEUnavailableError):
        _client(handler).get_bytes("https://www.bseindia.com/f.pdf")


def test_get_bytes_returns_empty_on_404_not_raise():
    # a genuinely-missing single file must NOT look like a BSE outage — return b"" so the
    # fetcher falls back to the other PDF base / records a per-file skip.
    handler = lambda req: httpx.Response(404, content=b"nope")
    assert _client(handler).get_bytes("https://www.bseindia.com/f.pdf") == b""


# --- transient-failure retries (a hung/flaky BSE shouldn't fail the whole build) ---

def _counting(responses):
    """A handler that yields the given responses/exceptions in order, counting calls."""
    state = {"n": 0}
    def handler(req):
        i = state["n"]; state["n"] += 1
        r = responses[min(i, len(responses) - 1)]
        if isinstance(r, Exception):
            raise r
        return r
    return handler, state


def test_get_json_retries_transient_5xx_then_succeeds():
    handler, state = _counting([httpx.Response(503), httpx.Response(503), httpx.Response(200, json={"ok": 1})])
    client = BSEClient(transport=httpx.MockTransport(handler), rate_delay=0, retry_backoff=0)
    assert client.get_json("https://api.bseindia.com/x", {})["ok"] == 1
    assert state["n"] == 3


def test_get_json_does_not_retry_transport_errors():
    handler, state = _counting([httpx.ConnectError("blip"), httpx.Response(200, json={"ok": 2})])
    client = BSEClient(transport=httpx.MockTransport(handler), rate_delay=0, retry_backoff=0)
    with pytest.raises(BSEUnavailableError, match="ConnectError: blip"):
        client.get_json("https://api.bseindia.com/x", {})
    assert state["n"] == 1


def test_get_json_gives_up_after_max_retries():
    handler, state = _counting([httpx.Response(503)])
    client = BSEClient(transport=httpx.MockTransport(handler), rate_delay=0, retry_backoff=0, max_retries=2)
    with pytest.raises(BSEUnavailableError):
        client.get_json("https://api.bseindia.com/x", {})
    assert state["n"] == 3   # 1 initial + 2 retries


def test_get_json_does_not_retry_4xx():
    handler, state = _counting([httpx.Response(404, json={})])
    client = BSEClient(transport=httpx.MockTransport(handler), rate_delay=0, retry_backoff=0)
    with pytest.raises(BSEUnavailableError):
        client.get_json("https://api.bseindia.com/x", {})
    assert state["n"] == 1   # client error → no retry


def test_get_bytes_retries_5xx_then_succeeds():
    handler, state = _counting([httpx.Response(503), httpx.Response(200, content=b"%PDF-1.7")])
    client = BSEClient(transport=httpx.MockTransport(handler), rate_delay=0, retry_backoff=0)
    assert client.get_bytes("https://www.bseindia.com/f.pdf").startswith(b"%PDF")
    assert state["n"] == 2


def test_get_bytes_404_is_not_retried():
    handler, state = _counting([httpx.Response(404)])
    client = BSEClient(transport=httpx.MockTransport(handler), rate_delay=0, retry_backoff=0)
    assert client.get_bytes("https://www.bseindia.com/f.pdf") == b""
    assert state["n"] == 1
