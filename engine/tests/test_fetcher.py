import json
import httpx
import pytest
from engine.bse_client import BSEClient
from engine.fetcher import list_filings, ANN_URL
from engine.models import FilingType
from engine.tests.conftest import FIXTURES


def _paged_client(pages: list[dict]) -> BSEClient:
    """Serve page N from `pages`, then empty Table to end pagination."""
    def handler(req):
        pageno = int(dict(req.url.params)["pageno"])
        body = pages[pageno - 1] if pageno <= len(pages) else {"Table": []}
        return httpx.Response(200, json=body)
    return BSEClient(transport=httpx.MockTransport(handler), rate_delay=0)


def test_filters_to_requested_types_only():
    page = json.loads((FIXTURES / "ann_page1.json").read_text())
    client = _paged_client([page])
    out = list_filings("532790", [FilingType.ANNUAL_REPORT, FilingType.RESULTS], years=5, client=client)
    ids = {f.news_id for f in out}
    assert ids == {"ar-1", "res-1"}          # noise-1 excluded
    ar = next(f for f in out if f.news_id == "ar-1")
    assert ar.kind is FilingType.ANNUAL_REPORT
    assert ar.date == "2025-07-01"           # DissemDT trimmed to YYYY-MM-DD
    assert ar.attachment == "ar1.pdf"


def test_stops_paginating_on_short_page():
    page = json.loads((FIXTURES / "ann_page1.json").read_text())  # 3 rows (<10) → stop after page 1
    calls = {"n": 0}
    def handler(req):
        calls["n"] += 1
        return httpx.Response(200, json=page)
    client = BSEClient(transport=httpx.MockTransport(handler), rate_delay=0)
    list_filings("532790", [FilingType.ANNUAL_REPORT], years=1, client=client)
    assert calls["n"] == 1


def test_sends_confirmed_params():
    seen = {}
    def handler(req):
        seen.update(dict(req.url.params))
        return httpx.Response(200, json={"Table": []})
    client = BSEClient(transport=httpx.MockTransport(handler), rate_delay=0)
    list_filings("532790", [FilingType.RESULTS], years=3, client=client)
    assert seen["strScrip"] == "532790"
    assert seen["strCat"] == "-1" and seen["subcategory"] == "-1"
    assert seen["strType"] == "C" and seen["strSearch"] == "P"
    assert len(seen["strPrevDate"]) == 8 and len(seen["strToDate"]) == 8
