import httpx
import pytest
from engine.bse_client import BSEClient
from engine.resolver import resolve
from engine.errors import CompanyNotFoundError
from engine.tests.conftest import FIXTURES


def _client_serving(html: str) -> BSEClient:
    return BSEClient(transport=httpx.MockTransport(lambda req: httpx.Response(200, text=html)),
                     rate_delay=0)


def test_single_match_is_primary():
    html = (FIXTURES / "peersmartsearch_tanla.html").read_text()
    out = resolve("TANLA", _client_serving(html))
    assert len(out) == 1
    assert out[0].scrip_code == "532790"
    assert out[0].company == "Tanla Platforms Ltd"
    assert out[0].is_primary is True


def test_multi_match_marks_only_quotemenuselect_primary():
    html = (FIXTURES / "peersmartsearch_reliance.html").read_text()
    out = resolve("RELIANCE", _client_serving(html))
    assert [c.scrip_code for c in out] == ["500325", "500390", "532712"]
    primaries = [c for c in out if c.is_primary]
    assert len(primaries) == 1 and primaries[0].scrip_code == "500325"


def test_no_match_raises_company_not_found():
    with pytest.raises(CompanyNotFoundError):
        resolve("ZЗ", _client_serving("<li>nothing here</li>"))


def test_resolve_surfaces_isin_when_present():
    html = (FIXTURES / "peersmartsearch_tanla.html").read_text()
    out = resolve("TANLA", _client_serving(html))
    assert out[0].isin == "INE483C01032"


def test_resolve_isin_none_when_absent():
    # the reliance fixture rows are stripped and carry no ISIN
    html = (FIXTURES / "peersmartsearch_reliance.html").read_text()
    out = resolve("RELIANCE", _client_serving(html))
    assert out[0].isin is None


def test_resolve_surfaces_symbol_when_present():
    html = (FIXTURES / "peersmartsearch_tanla.html").read_text()
    out = resolve("TANLA", _client_serving(html))
    assert out[0].symbol == "TANLA"


def test_resolve_symbol_none_when_absent():
    html = (FIXTURES / "peersmartsearch_reliance.html").read_text()
    out = resolve("RELIANCE", _client_serving(html))
    assert out[0].symbol is None


def test_symbol_is_full_ticker_not_the_bolded_query_match():
    # PeerSmartSearch bolds the typed substring; the real ticker is the <span>'s first token.
    # Searching "tita" must still yield symbol TITAN (not "TITA").
    html = ("\"<li class='quotemenu quotemenuselect' onclick=\\\"liclick('500114','Titan Company Ltd')\\\">"
            "<a><strong>TITA</strong>N COMPANY LTD<br /><span><strong>TITA</strong>N&nbsp;&nbsp;&nbsp;"
            "INE280A01028&nbsp;&nbsp;&nbsp;500114</span></a></li>\"")
    out = resolve("tita", _client_serving(html))
    assert out[0].symbol == "TITAN"
    assert out[0].isin == "INE280A01028"
