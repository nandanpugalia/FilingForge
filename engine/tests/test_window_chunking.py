"""BSE's announcements API answers a window longer than ~1 year with an EMPTY table — silently.
Seen live 2026-09-05 on PFC (532810): `--years 5` returned 0 announcements (only the annual-report
archive fallback), `--years 1` returned 116. So the listing must ask in windows of at most 365 days
and merge, counting a filing that straddles two windows once."""
from datetime import date, timedelta

import httpx
import pytest

from engine.bse_client import BSEClient
from engine.fetcher import list_filings
from engine.errors import BSEUnavailableError


def _row(news_id, day):
    return {"NEWSID": news_id, "DissemDT": f"{day.isoformat()}T10:00:00", "HEADLINE": f"Filing {news_id}",
            "ATTACHMENTNAME": f"{news_id}.pdf", "CATEGORYNAME": "Result", "SUBCATNAME": "Financial Results"}


def _bse_like_client(windows_seen):
    """Behaves like BSE: a window > 365 days -> empty; otherwise one row dated inside the window,
    plus a row on the window's start day (so adjacent windows overlap on one filing)."""
    def handler(req):
        p = dict(req.url.params)
        start = date.fromisoformat(f"{p['strPrevDate'][:4]}-{p['strPrevDate'][4:6]}-{p['strPrevDate'][6:]}")
        end = date.fromisoformat(f"{p['strToDate'][:4]}-{p['strToDate'][4:6]}-{p['strToDate'][6:]}")
        windows_seen.append((start, end))
        if (end - start).days > 365 or p["pageno"] != "1":
            return httpx.Response(200, json={"Table": []})
        mid = start + (end - start) // 2
        return httpx.Response(200, json={"Table": [_row(f"mid-{mid}", mid), _row(f"edge-{start}", start)]})
    return BSEClient(transport=httpx.MockTransport(handler), rate_delay=0)


def test_a_five_year_ask_becomes_windows_of_at_most_a_year_and_merges_them():
    seen = []
    out = list_filings("532810", [], 5, _bse_like_client(seen), everything=True)
    assert seen and all((e - s).days <= 365 for s, e in seen)
    assert min(s for s, _ in seen) <= date.today() - timedelta(days=365 * 5 - 1)
    assert max(e for _, e in seen) == date.today()
    mids = [f for f in out if f.news_id.startswith("mid-")]
    assert len(mids) == 5  # one per window: nothing was silently dropped


def test_a_filing_on_a_window_boundary_is_counted_once():
    seen = []
    out = list_filings("532810", [], 3, _bse_like_client(seen), everything=True)
    ids = [f.news_id for f in out]
    assert len(ids) == len(set(ids))


def test_a_one_year_ask_is_still_a_single_window():
    seen = []
    list_filings("532810", [], 1, _bse_like_client(seen), everything=True)
    assert len({(s, e) for s, e in seen}) == 1


def test_results_come_back_newest_first():
    out = list_filings("532810", [], 4, _bse_like_client([]), everything=True)
    dates = [f.date for f in out]
    assert dates == sorted(dates, reverse=True)


@pytest.mark.parametrize('years', [1, 2, 6, 25])
def test_every_requested_day_including_oldest_boundary_is_covered(years):
    seen = []
    list_filings('530871', [], years, _bse_like_client(seen), everything=True)
    covered = {start + timedelta(days=n) for start, end in seen
               for n in range((end - start).days + 1)}
    today = date.today()
    assert covered == {today - timedelta(days=n) for n in range(365 * years + 1)}


def test_shared_boundary_is_present_once_and_unsorted_rows_are_sorted():
    today = date.today()
    edge = today - timedelta(days=365)
    rows = [_row('oldest', today - timedelta(days=730)),
            _row('edge', edge), _row('newest', today)]
    def handler(req):
        p = dict(req.url.params)
        start, end = p['strPrevDate'], p['strToDate']
        hits = [r for r in rows if start <= r['DissemDT'][:10].replace('-', '') <= end]
        return httpx.Response(200, json={'Table': hits})
    client = BSEClient(transport=httpx.MockTransport(handler), rate_delay=0)
    out = list_filings('530871', [], 2, client, everything=True)
    assert [f.news_id for f in out] == ['newest', 'edge', 'oldest']


def test_pagination_restarts_in_each_window_and_keeps_later_pages():
    seen = []
    def handler(req):
        p = dict(req.url.params)
        seen.append((p['strPrevDate'], int(p['pageno'])))
        end = date.fromisoformat(f"{p['strToDate'][:4]}-{p['strToDate'][4:6]}-{p['strToDate'][6:]}")
        count = 50 if p['pageno'] == '1' else 1
        rows = [_row(f"{p['strPrevDate']}-{p['pageno']}-{i}", end) for i in range(count)]
        return httpx.Response(200, json={'Table': rows})
    out = list_filings('530871', [], 3,
        BSEClient(transport=httpx.MockTransport(handler), rate_delay=0), everything=True)
    assert len(out) == 153
    assert [page for _, page in seen] == [1, 2, 1, 2, 1, 2]


def test_empty_recent_window_does_not_hide_older_filings():
    today = date.today()
    def handler(req):
        end = req.url.params['strToDate']
        rows = [] if end == today.strftime('%Y%m%d') else [_row('older', today - timedelta(days=400))]
        return httpx.Response(200, json={'Table': rows})
    out = list_filings('530871', [], 2,
        BSEClient(transport=httpx.MockTransport(handler), rate_delay=0), everything=True)
    assert [f.news_id for f in out] == ['older']


def test_failed_older_window_raises_instead_of_returning_partial_success():
    today = date.today()
    def handler(req):
        if req.url.params['strToDate'] != today.strftime('%Y%m%d'):
            return httpx.Response(503)
        return httpx.Response(200, json={'Table': [_row('recent', today)]})
    client = BSEClient(transport=httpx.MockTransport(handler), rate_delay=0, max_retries=0)
    with pytest.raises(BSEUnavailableError):
        list_filings('530871', [], 2, client, everything=True)
