import pytest
from engine.models import Candidate
from engine.errors import CompanyNotFoundError, BSEUnavailableError


def test_resolve_returns_candidate_list(client, monkeypatch):
    import api.routes as routes
    def fake_resolve(name, client_):
        return [Candidate("500325", "Reliance Industries Ltd", True),
                Candidate("532712", "Reliance Communications Ltd", False)]
    monkeypatch.setattr(routes, "resolve", fake_resolve)
    r = client.post("/resolve", json={"company": "RELIANCE"})
    assert r.status_code == 200
    cands = r.json()["candidates"]
    assert len(cands) == 2
    assert cands[0] == {"scrip_code": "500325", "company": "Reliance Industries Ltd", "is_primary": True}


def test_resolve_unknown_company_is_404_friendly(client, monkeypatch):
    import api.routes as routes
    def fake_resolve(name, client_):
        raise CompanyNotFoundError(name)
    monkeypatch.setattr(routes, "resolve", fake_resolve)
    r = client.post("/resolve", json={"company": "ZZZQQ"})
    assert r.status_code == 404
    assert "couldn't find" in r.json()["user_message"].lower()
    assert "ZZZQQ" in r.json()["user_message"]


def test_resolve_bse_down_is_503_friendly(client, monkeypatch):
    import api.routes as routes
    def fake_resolve(name, client_):
        raise BSEUnavailableError("timeout")
    monkeypatch.setattr(routes, "resolve", fake_resolve)
    r = client.post("/resolve", json={"company": "TANLA"})
    assert r.status_code == 503
    assert "try again" in r.json()["user_message"].lower()


def test_resolve_rejects_empty_company(client):
    r = client.post("/resolve", json={"company": ""})
    assert r.status_code == 422
