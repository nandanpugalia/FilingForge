import json
import os
import httpx
import pytest
from engine.bse_client import BSEClient
from engine.library import build_library, refresh_library
from engine.models import CURATED_BY_KEY
from engine.errors import CompanyNotFoundError

AR = CURATED_BY_KEY["annual_report"]

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
    res = build_library("532790", "TANLA", tmp_path, [AR],
                        years=5, client=_full_client(), on_progress=events.append)
    company = tmp_path / "TANLA"
    assert sorted(res.downloaded) and len(res.downloaded) == 2 and not res.failed
    assert list((company / "annual-reports").glob("*.pdf"))
    assert list((company / "annual-reports").glob("*.md"))
    assert (company / "INDEX.md").exists()
    assert any(e.stage == "download" for e in events)   # progress emitted


def test_partial_failure_keeps_folder_valid(tmp_path):
    res = build_library("532790", "TANLA", tmp_path, [AR],
                        years=5, client=_full_client(ar2_ok=False), on_progress=None)
    assert len(res.downloaded) == 1 and len(res.failed) == 1
    assert res.ok is True
    assert (tmp_path / "TANLA" / "INDEX.md").exists()    # never corrupt


def test_refresh_pulls_only_new(tmp_path):
    build_library("532790", "TANLA", tmp_path, [AR],
                  years=5, client=_full_client(), on_progress=None)
    res2 = refresh_library(tmp_path / "TANLA", "532790", [AR],
                           years=5, client=_full_client(), on_progress=None)
    assert res2.downloaded == [] and len(res2.skipped) == 2   # idempotent: nothing new


def test_oserror_during_save_is_caught_not_fatal(tmp_path, monkeypatch):
    import engine.library as lib
    def boom(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(lib, "save_filing", boom)
    res = build_library("532790", "TANLA", tmp_path, [AR],
                        years=5, client=_full_client(), on_progress=None)
    assert len(res.failed) == 2 and not res.downloaded   # both recorded as failed, no crash
    assert (tmp_path / "TANLA" / "INDEX.md").exists()      # library still valid


def test_same_date_headline_different_newsid_both_kept(tmp_path):
    ann = {"Table": [
        {"NEWSID": "a", "DissemDT": "2025-07-01T10:00:00", "HEADLINE": "Annual Report",
         "ATTACHMENTNAME": "a.pdf", "CATEGORYNAME": "Others", "SUBCATNAME": "Reg. 34 (1) Annual Report"},
        {"NEWSID": "b", "DissemDT": "2025-07-01T10:00:00", "HEADLINE": "Annual Report",
         "ATTACHMENTNAME": "b.pdf", "CATEGORYNAME": "Others", "SUBCATNAME": "Reg. 34 (1) Annual Report"},
    ]}
    def handler(req):
        u = str(req.url)
        if "PeerSmartSearch" in u:
            return httpx.Response(200, text=_RESOLVE_HTML)
        if "AnnSubCategoryGetData" in u:
            p = int(dict(req.url.params)["pageno"])
            return httpx.Response(200, json=ann if p == 1 else {"Table": []})
        if "a.pdf" in u:
            return httpx.Response(200, content=b"%PDF-1.7 AAA")
        if "b.pdf" in u:
            return httpx.Response(200, content=b"%PDF-1.7 BBB")
        return httpx.Response(404)
    client = BSEClient(transport=httpx.MockTransport(handler), rate_delay=0)
    res = build_library("532790", "TANLA", tmp_path, [AR],
                        years=5, client=client, on_progress=None)
    pdfs = list((tmp_path / "TANLA" / "annual-reports").glob("*.pdf"))
    assert len(res.downloaded) == 2 and len(pdfs) == 2   # both survive — no silent overwrite


def test_build_writes_master_index_at_root(tmp_path):
    build_library("532790", "TANLA", tmp_path, [AR], years=5,
                  client=_full_client(), on_progress=None)
    assert (tmp_path / "INDEX.md").exists()
    assert "TANLA" in (tmp_path / "INDEX.md").read_text()


@pytest.mark.skipif(os.environ.get("FF_LIVE") != "1",
                    reason="live BSE test; set FF_LIVE=1 to run")
def test_live_tanla_smoke(tmp_path):
    from engine.bse_client import BSEClient
    client = BSEClient()
    try:
        res = build_library("532790", "TANLA", tmp_path, [AR],
                            years=2, client=client, on_progress=None)
    finally:
        client.close()
    assert res.ok and (tmp_path / "TANLA" / "INDEX.md").exists()
