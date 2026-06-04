import json
import httpx
import pytest
from engine.bse_client import BSEClient
from engine.library import build_library, refresh_library
from engine.models import FilingType
from engine.errors import CompanyNotFoundError

_RESOLVE_HTML = "\"<li class='quotemenu quotemenuselect' onclick=\\\"liclick('532790','Tanla Platforms Ltd')\\\"><a>T</a></li>\""
_ANN = {"Table": [
    {"NEWSID": "ar-1", "DissemDT": "2025-07-01T10:00:00", "HEADLINE": "Annual Report 2024-25",
     "ATTACHMENTNAME": "ar1.pdf", "CATEGORYNAME": "Others", "SUBCATNAME": "Reg. 34 (1) Annual Report"},
    {"NEWSID": "ar-2", "DissemDT": "2024-07-03T10:00:00", "HEADLINE": "Annual Report 2023-24",
     "ATTACHMENTNAME": "ar2.pdf", "CATEGORYNAME": "Others", "SUBCATNAME": "Reg. 34 (1) Annual Report"},
]}


def _full_client(ar2_ok=True):
    def handler(req):
        u = str(req.url)
        if "PeerSmartSearch" in u:
            return httpx.Response(200, text=_RESOLVE_HTML)
        if "AnnSubCategoryGetData" in u:
            pageno = int(dict(req.url.params)["pageno"])
            return httpx.Response(200, json=_ANN if pageno == 1 else {"Table": []})
        if "ar1.pdf" in u:
            return httpx.Response(200, content=b"%PDF-1.7 one")
        if "ar2.pdf" in u:
            return httpx.Response(200, content=b"%PDF-1.7 two" if ar2_ok else b"<html>broken</html>")
        return httpx.Response(404)
    return BSEClient(transport=httpx.MockTransport(handler), rate_delay=0)


def test_build_downloads_converts_and_indexes(tmp_path):
    events = []
    res = build_library("532790", "TANLA", tmp_path, [FilingType.ANNUAL_REPORT],
                        years=5, client=_full_client(), on_progress=events.append)
    company = tmp_path / "TANLA"
    assert sorted(res.downloaded) and len(res.downloaded) == 2 and not res.failed
    assert list((company / "annual-reports").glob("*.pdf"))
    assert list((company / "annual-reports").glob("*.md"))
    assert (company / "INDEX.md").exists()
    assert any(e.stage == "download" for e in events)   # progress emitted


def test_partial_failure_keeps_folder_valid(tmp_path):
    res = build_library("532790", "TANLA", tmp_path, [FilingType.ANNUAL_REPORT],
                        years=5, client=_full_client(ar2_ok=False), on_progress=None)
    assert len(res.downloaded) == 1 and len(res.failed) == 1
    assert res.ok is True
    assert (tmp_path / "TANLA" / "INDEX.md").exists()    # never corrupt


def test_refresh_pulls_only_new(tmp_path):
    build_library("532790", "TANLA", tmp_path, [FilingType.ANNUAL_REPORT],
                  years=5, client=_full_client(), on_progress=None)
    res2 = refresh_library(tmp_path / "TANLA", "532790", [FilingType.ANNUAL_REPORT],
                           years=5, client=_full_client(), on_progress=None)
    assert res2.downloaded == [] and len(res2.skipped) == 2   # idempotent: nothing new
