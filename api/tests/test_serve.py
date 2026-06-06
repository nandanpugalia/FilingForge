import os
import pytest
from fastapi.testclient import TestClient
from api.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    (tmp_path / "ACME" / "research_report").mkdir(parents=True)
    (tmp_path / "ACME" / "research_report" / "business_model.html").write_text("<h1>ok</h1>")
    (tmp_path / "secret.txt").write_text("nope")           # inside root, not a report
    (tmp_path.parent / "outside.txt").write_text("leak")   # OUTSIDE the library root
    monkeypatch.setenv("FF_TOKEN", "tok123")
    monkeypatch.setenv("FF_LIBRARY_ROOT", str(tmp_path))
    return TestClient(create_app())


def test_serves_in_library_file_with_token(client):
    r = client.get("/lib/ACME/research_report/business_model.html?token=tok123")
    assert r.status_code == 200 and "ok" in r.text


def test_rejects_missing_or_wrong_token(client):
    assert client.get("/lib/ACME/research_report/business_model.html").status_code == 403
    assert client.get("/lib/ACME/research_report/business_model.html?token=bad").status_code == 403


def test_rejects_path_traversal(client):
    assert client.get("/lib/../outside.txt?token=tok123").status_code in (400, 403, 404)


def test_rejects_url_encoded_traversal(client):
    # url-encoded and double-encoded ../ must not escape the root either
    assert client.get("/lib/%2e%2e%2foutside.txt?token=tok123").status_code in (400, 403, 404)
    assert client.get("/lib/%252e%252e%252foutside.txt?token=tok123").status_code in (400, 403, 404)


def test_no_directory_listing(client):
    assert client.get("/lib/ACME/research_report/?token=tok123").status_code == 404


def test_rejects_symlink_escape(client, tmp_path):
    # a symlink inside the root pointing outside must not be served
    link = tmp_path / "ACME" / "research_report" / "evil.html"
    link.symlink_to(tmp_path.parent / "outside.txt")
    assert client.get("/lib/ACME/research_report/evil.html?token=tok123").status_code == 404


def test_fails_closed_when_token_unset(tmp_path, monkeypatch):
    # If FF_TOKEN is somehow not configured, the route must serve NOTHING (fail closed),
    # never fall through on a None==None match.
    (tmp_path / "ACME" / "research_report").mkdir(parents=True)
    (tmp_path / "ACME" / "research_report" / "business_model.html").write_text("<h1>ok</h1>")
    monkeypatch.delenv("FF_TOKEN", raising=False)
    monkeypatch.setenv("FF_LIBRARY_ROOT", str(tmp_path))
    c = TestClient(create_app())
    assert c.get("/lib/ACME/research_report/business_model.html").status_code == 403
    assert c.get("/lib/ACME/research_report/business_model.html?token=").status_code == 403


def test_fails_when_no_root_configured(tmp_path, monkeypatch):
    # With a valid token but NO library root configured, refuse (503) rather than
    # resolve an empty path to the process cwd and serve files from there.
    monkeypatch.setenv("FF_TOKEN", "tok123")
    monkeypatch.delenv("FF_LIBRARY_ROOT", raising=False)
    c = TestClient(create_app())
    assert c.get("/lib/anything.html?token=tok123").status_code == 503
