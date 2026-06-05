"""CORS is the browser's gate on which page-origins may call the loopback engine.
The engine binds 127.0.0.1, but the user's OWN browser (or a malicious local page)
can still POST to it — so the mutating endpoints must only accept the real Tauri /
dev webview origins, not arbitrary internet sites."""


def _preflight(client, origin: str, path: str = "/build"):
    return client.options(
        path,
        headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
    )


def test_cors_allows_mac_tauri_origin(client):
    r = _preflight(client, "tauri://localhost")
    assert r.headers.get("access-control-allow-origin") == "tauri://localhost"


def test_cors_allows_windows_tauri_origin_either_scheme(client):
    for origin in ("http://tauri.localhost", "https://tauri.localhost"):
        r = _preflight(client, origin)
        assert r.headers.get("access-control-allow-origin") == origin


def test_cors_allows_dev_localhost_any_port(client):
    r = _preflight(client, "http://localhost:5173")
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_rejects_internet_origin(client):
    r = _preflight(client, "https://evil.example.com")
    assert r.headers.get("access-control-allow-origin") is None
