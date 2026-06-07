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
    # year-nested layout: <category>/<YYYY>/<file>.{pdf,md}; rglob catches the depth
    assert list((company / "annual-reports").rglob("*.pdf"))
    assert list((company / "annual-reports").rglob("*.md"))
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
    pdfs = list((tmp_path / "TANLA" / "annual-reports").rglob("*.pdf"))
    assert len(res.downloaded) == 2 and len(pdfs) == 2   # both survive — no silent overwrite


def test_build_writes_master_index_at_root(tmp_path):
    build_library("532790", "TANLA", tmp_path, [AR], years=5,
                  client=_full_client(), on_progress=None)
    assert (tmp_path / "INDEX.md").exists()
    assert "TANLA" in (tmp_path / "INDEX.md").read_text()


def test_preview_counts_without_downloading(tmp_path):
    from engine.library import preview_library
    pv = preview_library("532790", tmp_path, "TANLA", [AR], years=5, client=_full_client())
    assert pv["total"] == 2 and pv["new"] == 2 and pv["have"] == 0
    labels = {c["label"]: c["count"] for c in pv["by_category"]}
    assert labels["Annual Reports"] == 2
    # preview NEVER touches disk — no company folder, no downloads
    assert not (tmp_path / "TANLA").exists()


def test_preview_marks_already_have_when_library_exists(tmp_path):
    from engine.library import preview_library
    # build once so the seen-ledger knows both filings
    build_library("532790", "TANLA", tmp_path, [AR], years=5, client=_full_client(), on_progress=None)
    pv = preview_library("532790", tmp_path, "TANLA", [AR], years=5, client=_full_client())
    assert pv["total"] == 2 and pv["have"] == 2 and pv["new"] == 0


def test_cancel_stops_download_and_leaves_library_consistent(tmp_path):
    # should_cancel returns True on the very first check → no filings downloaded, but the
    # library must still be valid (INDEX rebuilt, helper written) and flagged cancelled.
    from engine.report_helper import HELPER_NAME, HELPER_DIR
    res = build_library("532790", "TANLA", tmp_path, [AR], years=5,
                        client=_full_client(), on_progress=None, should_cancel=lambda: True)
    assert res.cancelled is True
    assert res.downloaded == []
    assert (tmp_path / "TANLA" / "INDEX.md").exists()       # never corrupt
    assert (tmp_path / HELPER_DIR / HELPER_NAME).exists()


def test_cancel_after_first_keeps_completed_filings_whole(tmp_path):
    # cancel AFTER the first filing → exactly one complete (pdf+md), no .part remnants
    calls = {"n": 0}
    def cancel():
        calls["n"] += 1
        return calls["n"] > 1   # 1st check False (download #1), 2nd check True (stop)
    res = build_library("532790", "TANLA", tmp_path, [AR], years=5,
                        client=_full_client(), on_progress=None, should_cancel=cancel)
    assert res.cancelled is True
    assert len(res.downloaded) == 1
    company = tmp_path / "TANLA"
    pdfs = list(company.rglob("*.pdf"))
    assert len(pdfs) == 1 and pdfs[0].with_suffix(".md").exists()   # the one we kept is whole
    assert list(company.rglob("*.part")) == []                       # no half-files left


def test_build_writes_report_helper(tmp_path):
    # The app-managed report template lands in the _filingforge/ system folder so every skill reads it.
    from engine.report_helper import HELPER_NAME, HELPER_DIR
    build_library("532790", "TANLA", tmp_path, [AR], years=5,
                  client=_full_client(), on_progress=None)
    helper = tmp_path / HELPER_DIR / HELPER_NAME
    assert helper.exists()
    assert "moat-grid" in helper.read_text(encoding="utf-8")   # the locked house style


def test_build_expands_tilde_in_root(tmp_path, monkeypatch):
    # A "~/..." dest must expand to the user's home, NOT create a literal "~" folder.
    # We point home at tmp_path so the test stays sandboxed and self-cleaning.
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows parity
    build_library("532790", "TANLA", "~/fftest_tmp", [AR], years=5,
                  client=_full_client(), on_progress=None)
    assert (tmp_path / "fftest_tmp" / "TANLA" / "INDEX.md").exists()  # expanded
    from pathlib import Path
    assert not (Path.cwd() / "~").exists()                           # no literal "~"


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
