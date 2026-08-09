"""Merging BSE's two filing sources into one listing.

Announcements carry everything from ~2010 but only carry annual reports from
2015 (LODR Reg. 34(1)). The archive carries annual reports from 1997. A library
wants both, with the overlap counted once.
"""
import httpx

from engine.bse_client import BSEClient
from engine.fetcher import list_all_filings
from engine.models import CURATED_BY_KEY

AR_SPEC = CURATED_BY_KEY["annual_report"]
RESULTS_SPEC = CURATED_BY_KEY["results"]

ANN_ROWS = {"Table": [
    {"NEWSID": "ann-ar-2026", "DissemDT": "2026-06-19T10:00:00", "HEADLINE": "Annual Report 2026",
     "ATTACHMENTNAME": "shared-2026.pdf", "CATEGORYNAME": "Others",
     "SUBCATNAME": "Reg. 34 (1) Annual Report"},
    {"NEWSID": "ann-res", "DissemDT": "2026-05-01T10:00:00", "HEADLINE": "Q4 Results",
     "ATTACHMENTNAME": "res.pdf", "CATEGORYNAME": "Result", "SUBCATNAME": "Financial Results"},
]}

AR_ROWS = {"Table": [
    # Same document the announcements feed already offers, as a full URL.
    {"Scripcode": "500495", "Year": "2026", "Fld_AuthoriseDate": "2026-06-19T10:00:00",
     "PDFDownload": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/shared-2026.pdf"},
    # Pre-2015: exists ONLY in the archive.
    {"Scripcode": "500495", "Year": "2003", "Fld_AuthoriseDate": None,
     "PDFDownload": "https://www.bseindia.com/HIS_ANN_RPT/HISTANNR/2003/X-500495-MARCH-2003.PDF"},
]}


def _client(ann=ANN_ROWS, archive=AR_ROWS, archive_status=200):
    def handler(req):
        if "AnnualReport_New" in str(req.url):
            return httpx.Response(archive_status, json=archive)
        return httpx.Response(200, json=ann if int(dict(req.url.params)["pageno"]) == 1 else {"Table": []})
    return BSEClient(transport=httpx.MockTransport(handler), rate_delay=0)


def test_keeps_the_announcement_filings():
    out = list_all_filings("500495", [AR_SPEC, RESULTS_SPEC], 5, _client())
    assert "ann-res" in {f.news_id for f in out}


def test_adds_pre_2015_reports_that_only_the_archive_has():
    out = list_all_filings("500495", [AR_SPEC], 25, _client())
    assert "AR-500495-2003" in {f.news_id for f in out}


def test_counts_a_report_in_both_sources_once():
    out = list_all_filings("500495", [AR_SPEC], 25, _client())
    reports_2026 = [f for f in out if "2026" in f.headline]
    assert len(reports_2026) == 1


def test_prefers_the_announcement_id_so_existing_libraries_do_not_redownload():
    # already_have() keys on news_id. If the archive entry won, every existing
    # user would re-fetch an annual report they already have.
    out = list_all_filings("500495", [AR_SPEC], 25, _client())
    assert "ann-ar-2026" in {f.news_id for f in out}
    assert "AR-500495-2026" not in {f.news_id for f in out}


def test_does_not_touch_the_archive_when_annual_reports_are_not_selected():
    seen = []

    def handler(req):
        seen.append(str(req.url))
        if "AnnualReport_New" in str(req.url):
            return httpx.Response(200, json=AR_ROWS)
        return httpx.Response(200, json=ANN_ROWS if int(dict(req.url.params)["pageno"]) == 1 else {"Table": []})

    client = BSEClient(transport=httpx.MockTransport(handler), rate_delay=0)
    list_all_filings("500495", [RESULTS_SPEC], 5, client)
    assert not any("AnnualReport_New" in u for u in seen)


def test_everything_mode_still_reads_the_archive():
    out = list_all_filings("500495", [], 25, _client(), everything=True)
    assert "AR-500495-2003" in {f.news_id for f in out}


def test_an_unavailable_archive_does_not_lose_the_announcements():
    # Some scrips 404 the archive endpoint. That must degrade, not fail the pull.
    client = BSEClient(
        transport=_client(archive_status=500)._client._transport,
        rate_delay=0,
        retry_backoff=0,
    )
    out = list_all_filings("500495", [AR_SPEC, RESULTS_SPEC], 25, client)
    assert {"ann-ar-2026", "ann-res"} <= {f.news_id for f in out}
