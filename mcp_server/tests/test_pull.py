"""Tests for the pull half of the MCP surface.

A model drives these, so the rule that matters is: never silently guess which
company was meant. An ambiguous name comes back as choices, not as a download.
"""
import pytest

from engine.models import Candidate, LibraryResult
from mcp_server.tools import pull_company, refresh_company


class _Recorder:
    """Stands in for the engine calls so no test touches BSE or the disk."""

    def __init__(self, candidates, result=None):
        self.candidates = candidates
        self.result = result or LibraryResult(downloaded=["a", "b"], skipped=["c"])
        self.build_args = None
        self.refresh_args = None

    def resolve(self, name, client):
        return self.candidates

    def build(self, scrip_code, ticker, root, specs, years, client, **kw):
        self.build_args = dict(scrip_code=scrip_code, ticker=ticker, root=root,
                               specs=specs, years=years, **kw)
        return self.result

    def refresh(self, company, scrip_code, specs, years, client, **kw):
        self.refresh_args = dict(company=company, scrip_code=scrip_code,
                                 specs=specs, years=years, **kw)
        return self.result


ESCORTS = Candidate(scrip_code="500495", company="Escorts Kubota Limited",
                    is_primary=True, symbol="ESCORTS")
OTHER = Candidate(scrip_code="500496", company="Escorts Finance Limited", symbol="ESCORTSFIN")


def _patch(monkeypatch, rec):
    monkeypatch.setattr("mcp_server.tools._resolve", rec.resolve)
    monkeypatch.setattr("mcp_server.tools._build_library", rec.build)
    monkeypatch.setattr("mcp_server.tools._refresh_library", rec.refresh)


# ---------------------------------------------------------------- pull_company

def test_pulls_when_the_name_resolves_to_one_company(monkeypatch, tmp_path):
    rec = _Recorder([ESCORTS])
    _patch(monkeypatch, rec)
    out = pull_company("escorts", tmp_path, years=5, client=object())
    assert out["status"] == "built"
    assert out["ticker"] == "ESCORTS"
    assert out["downloaded"] == 2 and out["skipped"] == 1


def test_passes_the_resolved_scrip_and_years_through_to_the_engine(monkeypatch, tmp_path):
    rec = _Recorder([ESCORTS])
    _patch(monkeypatch, rec)
    pull_company("escorts", tmp_path, years=25, client=object())
    assert rec.build_args["scrip_code"] == "500495"
    assert rec.build_args["years"] == 25


def test_defaults_to_the_high_signal_categories(monkeypatch, tmp_path):
    rec = _Recorder([ESCORTS])
    _patch(monkeypatch, rec)
    pull_company("escorts", tmp_path, years=5, client=object())
    keys = sorted(s.key for s in rec.build_args["specs"])
    assert keys == ["annual_report", "concall", "investor_ppt", "results"]


def test_honours_an_explicit_category_choice(monkeypatch, tmp_path):
    rec = _Recorder([ESCORTS])
    _patch(monkeypatch, rec)
    pull_company("escorts", tmp_path, years=5, client=object(), categories=["annual_report"])
    assert [s.key for s in rec.build_args["specs"]] == ["annual_report"]


def test_an_unknown_category_is_rejected_rather_than_ignored(monkeypatch, tmp_path):
    rec = _Recorder([ESCORTS])
    _patch(monkeypatch, rec)
    with pytest.raises(ValueError):
        pull_company("escorts", tmp_path, years=5, client=object(), categories=["nonsense"])


def test_an_ambiguous_name_returns_choices_and_downloads_nothing(monkeypatch, tmp_path):
    rec = _Recorder([ESCORTS, OTHER])
    _patch(monkeypatch, rec)
    out = pull_company("escorts", tmp_path, years=5, client=object())
    assert out["status"] == "ambiguous"
    assert rec.build_args is None
    assert {c["scrip_code"] for c in out["candidates"]} == {"500495", "500496"}


def test_an_unresolvable_name_says_so_and_downloads_nothing(monkeypatch, tmp_path):
    rec = _Recorder([])
    _patch(monkeypatch, rec)
    out = pull_company("zzzz", tmp_path, years=5, client=object())
    assert out["status"] == "not_found"
    assert rec.build_args is None


def test_a_scrip_code_skips_resolution_entirely(monkeypatch, tmp_path):
    rec = _Recorder([])          # resolve would find nothing; must not be consulted
    _patch(monkeypatch, rec)
    out = pull_company("500495", tmp_path, years=5, client=object(), ticker="ESCORTS")
    assert out["status"] == "built"
    assert rec.build_args["scrip_code"] == "500495"


# ------------------------------------------------------------- refresh_company

def test_refreshes_an_existing_company(monkeypatch, tmp_path):
    (tmp_path / "ESCORTS").mkdir()
    rec = _Recorder([ESCORTS])
    _patch(monkeypatch, rec)
    out = refresh_company(tmp_path, "ESCORTS", client=object())
    assert out["status"] == "refreshed"
    assert rec.refresh_args["scrip_code"] == "500495"


def test_refusing_to_refresh_a_company_that_is_not_in_the_library(monkeypatch, tmp_path):
    rec = _Recorder([ESCORTS])
    _patch(monkeypatch, rec)
    out = refresh_company(tmp_path, "NOPE", client=object())
    assert out["status"] == "not_in_library"
    assert rec.refresh_args is None
