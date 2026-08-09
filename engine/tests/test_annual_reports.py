"""The annual-report archive: BSE's second, older filing source.

Annual reports only appear in the announcements feed from 2015, when LODR
Reg. 34(1) began requiring them. BSE's separate annual-report archive carries
them from 1997 — for delisted companies as well as live ones — so this source
is what takes a library's coverage back two decades.
"""
import json

import httpx
import pytest

from engine.bse_client import BSEClient
from engine.fetcher import AR_URL, download_filing, list_annual_reports
from engine.models import Filing
from engine.tests.conftest import FIXTURES


def _client(body):
    return BSEClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json=body)),
        rate_delay=0,
    )


def _archive():
    return json.loads((FIXTURES / "annual_reports.json").read_text())


# ------------------------------------------------------------------- listing

def test_lists_one_filing_per_archived_year():
    out = list_annual_reports("500495", _client(_archive()))
    assert [f.headline for f in out] == [
        "Annual Report 2026",
        "Annual Report 2012",
        "Annual Report 2000",
    ]


def test_lands_everything_in_the_annual_reports_folder():
    out = list_annual_reports("500495", _client(_archive()))
    assert all(f.folder == "annual-reports" for f in out)
    assert all(f.category == "Annual Reports" for f in out)


def test_news_id_is_stable_across_runs_so_reruns_skip_not_redownload():
    out = list_annual_reports("500495", _client(_archive()))
    assert [f.news_id for f in out] == [
        "AR-500495-2026",
        "AR-500495-2012",
        "AR-500495-2000",
    ]


def test_keeps_the_absolute_pdf_url_as_the_attachment():
    # Unlike announcements, the archive hands back a full URL — and three
    # different shapes of it, depending on the era the report was filed in.
    out = list_annual_reports("500495", _client(_archive()))
    assert out[0].attachment.endswith("/AttachHis/aa4acd39-762b-4cf1-9948-7ad5537f6059.pdf")
    assert out[1].attachment.endswith("/bseplus/AnnualReport/500495/5004950912.pdf")
    assert out[2].attachment.endswith("/HIS_ANN_RPT/HISTANNR/2000/ESCORTS_LTD-500495-MARCH-2000.PDF")


def test_uses_the_real_authorisation_date_when_bse_supplies_one():
    out = list_annual_reports("500495", _client(_archive()))
    assert out[1].date == "2013-02-22"


def test_falls_back_to_the_financial_year_end_for_pre_2006_records():
    # BSE leaves Fld_AuthoriseDate null on the oldest reports. The date is only
    # used for ordering and the filename prefix, and the year is carried in the
    # headline, so the Indian FY-end is a safe stand-in.
    out = list_annual_reports("500495", _client(_archive()))
    assert out[2].date == "2000-03-31"


def test_skips_a_year_with_no_pdf_link():
    out = list_annual_reports("500495", _client(_archive()))
    assert all("1998" not in f.headline for f in out)


def test_returns_newest_year_first():
    years = [f.headline.split()[-1] for f in list_annual_reports("500495", _client(_archive()))]
    assert years == sorted(years, reverse=True)


def test_an_empty_archive_yields_no_filings():
    assert list_annual_reports("500495", _client({"Table": []})) == []


def test_a_company_bse_does_not_recognise_yields_no_filings():
    assert list_annual_reports("999999", _client({})) == []


def test_years_limits_how_far_back_the_archive_is_read():
    out = list_annual_reports("500495", _client(_archive()), years=20)
    assert [f.headline for f in out] == ["Annual Report 2026", "Annual Report 2012"]


def test_sends_the_scrip_code_to_the_archive_endpoint():
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        seen["params"] = dict(req.url.params)
        return httpx.Response(200, json=_archive())

    client = BSEClient(transport=httpx.MockTransport(handler), rate_delay=0)
    list_annual_reports("500495", client)
    assert seen["url"].startswith(AR_URL)
    assert seen["params"]["scripcode"] == "500495"


# --------------------------------------------------- downloading by full URL

def _absolute(url="https://www.bseindia.com/HIS_ANN_RPT/HISTANNR/2000/X-500495-MARCH-2000.PDF"):
    return Filing(news_id="AR-500495-2000", date="2000-03-31",
                  headline="Annual Report 2000", attachment=url,
                  folder="annual-reports", category="Annual Reports")


def test_downloads_an_absolute_attachment_from_its_own_url():
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        return httpx.Response(200, content=b"%PDF-1.4 archived")

    client = BSEClient(transport=httpx.MockTransport(handler), rate_delay=0)
    assert download_filing(_absolute(), client).startswith(b"%PDF-")
    assert "AttachHis" not in seen["url"]
    assert seen["url"].endswith("X-500495-MARCH-2000.PDF")


def test_an_absolute_attachment_that_is_not_a_pdf_still_raises_download_error():
    from engine.errors import DownloadError

    client = BSEClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, content=b"<html>")),
        rate_delay=0,
    )
    with pytest.raises(DownloadError):
        download_filing(_absolute(), client)
