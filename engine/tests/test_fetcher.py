import json
import httpx
import pytest
from engine.bse_client import BSEClient
from engine.fetcher import list_filings, ANN_URL, download_filing
from engine.models import CURATED_BY_KEY, Filing
from engine.tests.conftest import FIXTURES


def _paged_client(pages):
    def handler(req):
        pageno = int(dict(req.url.params)["pageno"])
        body = pages[pageno - 1] if pageno <= len(pages) else {"Table": []}
        return httpx.Response(200, json=body)
    return BSEClient(transport=httpx.MockTransport(handler), rate_delay=0)


def test_filters_to_requested_specs_only():
    page = json.loads((FIXTURES / "ann_page1.json").read_text())
    client = _paged_client([page])
    specs = [CURATED_BY_KEY["annual_report"], CURATED_BY_KEY["results"]]
    out = list_filings("532790", specs, years=5, client=client)
    assert {f.news_id for f in out} == {"ar-1", "res-1"}
    ar = next(f for f in out if f.news_id == "ar-1")
    assert ar.folder == "annual-reports" and ar.category == "Annual Reports"
    assert ar.date == "2025-07-01" and ar.attachment == "ar1.pdf"


def test_everything_keeps_all_rows_with_attachment_foldered_by_category():
    page = json.loads((FIXTURES / "ann_page1.json").read_text())
    client = _paged_client([page])
    out = list_filings("532790", [], years=5, client=client, everything=True)
    assert {f.news_id for f in out} == {"ar-1", "res-1", "noise-1"}
    noise = next(f for f in out if f.news_id == "noise-1")
    assert noise.folder == "insider-trading-sast"
    assert noise.category == "Insider Trading / SAST"


def test_everything_keeps_linked_document_categories_in_canonical_folders():
    rows = {"Table": [
        {"NEWSID": "ar", "DissemDT": "2026-07-01", "HEADLINE": "Annual Report",
         "ATTACHMENTNAME": "ar.pdf", "CATEGORYNAME": "Others", "SUBCATNAME": "Reg. 34 (1) Annual Report"},
        {"NEWSID": "res", "DissemDT": "2026-07-02", "HEADLINE": "Financial Results",
         "ATTACHMENTNAME": "res.pdf", "CATEGORYNAME": "Result", "SUBCATNAME": "Financial Results"},
        {"NEWSID": "ppt", "DissemDT": "2026-07-03", "HEADLINE": "Investor Presentation",
         "ATTACHMENTNAME": "ppt.pdf", "CATEGORYNAME": "Company Update", "SUBCATNAME": "Investor Presentation"},
        {"NEWSID": "cc", "DissemDT": "2026-07-04", "HEADLINE": "Earnings Call Transcript",
         "ATTACHMENTNAME": "cc.pdf", "CATEGORYNAME": "Company Update", "SUBCATNAME": "Earnings Call Transcript"},
    ]}

    out = list_filings("543210", [], years=1, client=_paged_client([rows]), everything=True)

    assert {f.news_id: f.folder for f in out} == {
        "ar": "annual-reports", "res": "quarterly",
        "ppt": "investor-ppts", "cc": "concalls",
    }


def test_wildcard_spec_matches_any_subcat():
    rows = {"Table": [
        {"NEWSID": "d1", "DissemDT": "2025-05-01T10:00:00", "HEADLINE": "Dividend",
         "ATTACHMENTNAME": "d1.pdf", "CATEGORYNAME": "Corp. Action", "SUBCATNAME": "Dividend"},
        {"NEWSID": "d2", "DissemDT": "2025-05-02T10:00:00", "HEADLINE": "Record Date",
         "ATTACHMENTNAME": "d2.pdf", "CATEGORYNAME": "Corp. Action", "SUBCATNAME": "Record Date"},
    ]}
    client = _paged_client([rows])
    out = list_filings("532790", [CURATED_BY_KEY["corp_actions"]], years=1, client=client)
    assert {f.news_id for f in out} == {"d1", "d2"}
    assert all(f.folder == "corp-actions" for f in out)


def test_sends_confirmed_params_and_stops_on_short_page():
    seen = {}
    def handler(req):
        seen.update(dict(req.url.params))
        page = json.loads((FIXTURES / "ann_page1.json").read_text())
        return httpx.Response(200, json=page)
    client = BSEClient(transport=httpx.MockTransport(handler), rate_delay=0)
    list_filings("532790", [CURATED_BY_KEY["results"]], years=3, client=client)
    assert seen["strScrip"] == "532790" and seen["strCat"] == "-1"
    assert seen["subcategory"] == "-1" and seen["strType"] == "C" and seen["strSearch"] == "P"
    assert len(seen["strPrevDate"]) == 8 and len(seen["strToDate"]) == 8


def _f(att="ar1.pdf"):
    return Filing(news_id="ar-1", date="2025-07-01", headline="Annual Report",
                  attachment=att, folder="annual-reports", category="Annual Reports")


def test_download_prefers_attachhis_pdf_bytes():
    def handler(req):
        if "AttachHis" in str(req.url):
            return httpx.Response(200, content=b"%PDF-1.7 real")
        return httpx.Response(200, content=b"<html>stale AttachLive</html>")
    client = BSEClient(transport=httpx.MockTransport(handler), rate_delay=0)
    assert download_filing(_f(), client).startswith(b"%PDF-")


def test_download_falls_back_to_attachlive_when_his_missing():
    def handler(req):
        if "AttachHis" in str(req.url):
            return httpx.Response(404, content=b"nope")
        return httpx.Response(200, content=b"%PDF-1.4 fallback")
    client = BSEClient(transport=httpx.MockTransport(handler), rate_delay=0)
    assert download_filing(_f(), client).startswith(b"%PDF-")


def test_download_raises_download_error_when_no_pdf_anywhere():
    from engine.errors import DownloadError
    handler = lambda req: httpx.Response(200, content=b"<html>not a pdf</html>")
    client = BSEClient(transport=httpx.MockTransport(handler), rate_delay=0)
    with pytest.raises(DownloadError):
        download_filing(_f(), client)


@pytest.mark.parametrize("payload", [
    {"Error": "service unavailable"}, {"Table": "unavailable"}, {"Table": [None]},
    {"Error": "service unavailable", "Table": None}, [],
])
def test_error_payload_is_not_treated_as_empty_history(payload):
    from engine.errors import BSEUnavailableError

    with pytest.raises(BSEUnavailableError, match="invalid BSE table") as caught:
        list_filings("500495", [], 1, _paged_client([payload]), everything=True)
    assert caught.value.endpoint == ANN_URL and caught.value.page == "1"


def test_reported_total_handles_short_pages_without_an_extra_request():
    rows = json.loads((FIXTURES / "ann_page1.json").read_text())["Table"]
    pages = []

    def handler(req):
        page = int(req.url.params["pageno"])
        pages.append(page)
        assert page in (1, 2)
        return httpx.Response(200, json={"Table": rows[:2] if page == 1 else rows[2:],
                                         "Table1": [{"ROWCNT": 3}]})

    with_client = BSEClient(transport=httpx.MockTransport(handler), rate_delay=0)
    filings = list_filings("500495", [], 1, with_client, everything=True)
    assert len(filings) == 3
    assert pages == [1, 2]


@pytest.mark.parametrize("page_cap", [1, 50])
def test_incomplete_announcements_fail_instead_of_returning_partial_history(monkeypatch, page_cap):
    from engine.errors import BSEUnavailableError

    monkeypatch.setattr("engine.fetcher._MAX_PAGES", page_cap)
    rows = json.loads((FIXTURES / "ann_page1.json").read_text())["Table"]
    client = _paged_client([{"Table": rows, "Table1": [{"ROWCNT": 6}]}, {"Table": []}])
    with pytest.raises(BSEUnavailableError, match="incomplete BSE listing") as caught:
        list_filings("500495", [], 1, client, everything=True)
    assert caught.value.endpoint == ANN_URL and caught.value.page == (1 if page_cap == 1 else 2)


def test_download_tries_attachlive_if_attachhis_is_blocked():
    def handler(req):
        if "AttachHis" in req.url.path:
            return httpx.Response(403, text="Access Denied")
        assert "AttachLive" in req.url.path
        return httpx.Response(200, content=b"%PDF-1.4 live")

    client = BSEClient(transport=httpx.MockTransport(handler), rate_delay=0)
    assert download_filing(_f(), client) == b"%PDF-1.4 live"
