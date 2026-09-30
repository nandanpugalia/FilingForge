"""Offline regressions for the September 2026 BSE TLS fingerprint block."""
import json

import httpx
import pytest
from curl_cffi import requests as curl_requests

from engine.bse_client import BSEClient
from engine.errors import BSEUnavailableError
from engine.fetcher import ANN_URL, AR_URL, download_filing, list_annual_reports, list_filings
from engine.models import Filing
from engine.resolver import URL, resolve

BLOCK = b'<html><h1>Access Denied</h1><p>https://errors.edgesuite.net/18.example</p></html>'


def response(status=200, body=b'{"ok": true}'):
    result = curl_requests.Response()
    result.status_code = status
    result.content = body
    return result


@pytest.fixture
def wire(monkeypatch):
    """Replace only socket I/O, keeping real curl sessions and response objects."""
    calls, sessions = [], []
    replies = []

    def get(session, url, **kwargs):
        calls.append((session.impersonate, url, kwargs.get('params')))
        sessions.append(session)
        result = replies.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    # The pre-fix HTTPX client must fail offline as it does against Akamai.
    monkeypatch.setattr(httpx.HTTPTransport, 'handle_request',
                        lambda self, req: httpx.Response(403, content=BLOCK))
    monkeypatch.setattr(curl_requests.Session, 'get', get)
    return replies, calls, sessions


def test_default_client_uses_chrome_with_profile_headers_and_verified_tls():
    client = BSEClient()
    try:
        session = client._client
        assert isinstance(session, curl_requests.Session)
        assert session.impersonate == 'chrome'
        assert session.verify is not False
        assert session.default_headers is True
        # curl supplies the matching UA and client hints for each fingerprint.
        assert 'user-agent' not in session.headers
        assert 'sec-ch-ua' not in session.headers
        assert 'sec-ch-ua-platform' not in session.headers
        assert session.headers['Referer'] == 'https://www.bseindia.com/'
        assert session.timeout == (10.0, 30.0)
        assert session.allow_redirects is True
    finally:
        client.close()


def test_403_falls_back_to_safari_on_a_separate_connection(wire):
    replies, calls, sessions = wire
    replies.extend([response(403, BLOCK), response()])
    client = BSEClient(rate_delay=0, max_retries=0)
    try:
        assert client.get_json(ANN_URL, {'pageno': '1'}) == {'ok': True}
        assert calls == [('chrome', ANN_URL, {'pageno': '1'}),
                         ('safari17_0', ANN_URL, {'pageno': '1'})]
        assert sessions[0] is not sessions[1]
    finally:
        client.close()
    assert all(session._closed for session in sessions)


@pytest.mark.parametrize('method', ['get_json', 'get_text', 'get_bytes'])
def test_both_profiles_blocked_raise_status_and_fingerprint_message(wire, method):
    replies, calls, _ = wire
    replies.extend([response(403, BLOCK), response(403, BLOCK)])
    client = BSEClient(rate_delay=0, retry_backoff=0)
    try:
        args = (ANN_URL,) if method == 'get_bytes' else (ANN_URL, {})
        with pytest.raises(BSEUnavailableError, match=r'HTTP 403.*fingerprint block') as error:
            getattr(client, method)(*args)
        assert ANN_URL in str(error.value)
        assert 'fingerprint' not in error.value.user_message
        assert [call[0] for call in calls] == ['chrome', 'safari17_0']
    finally:
        client.close()


def test_plain_403_still_falls_back_but_is_not_labelled_a_fingerprint_block(wire):
    replies, calls, _ = wire
    replies.extend([response(403, b'Forbidden'), response(403, b'Forbidden')])
    client = BSEClient(rate_delay=0)
    try:
        with pytest.raises(BSEUnavailableError, match='HTTP 403') as error:
            client.get_text(URL, {})
        assert 'fingerprint block' not in str(error.value)
        assert [call[0] for call in calls] == ['chrome', 'safari17_0']
    finally:
        client.close()


@pytest.mark.parametrize('status', [429, 500, 501, 502, 503, 504, 599])
def test_transient_status_retries_same_profile_and_honours_budget(wire, status):
    replies, calls, _ = wire
    replies.extend([response(status)] * 3)
    client = BSEClient(rate_delay=0, retry_backoff=0, max_retries=2)
    try:
        with pytest.raises(BSEUnavailableError, match=f'HTTP {status}'):
            client.get_json(ANN_URL, {})
        assert [call[0] for call in calls] == ['chrome'] * 3
    finally:
        client.close()


def test_fallback_does_not_reset_the_transient_retry_budget(wire):
    replies, calls, _ = wire
    replies.extend([response(503), response(403, BLOCK), response(429), response()])
    client = BSEClient(rate_delay=0, retry_backoff=0, max_retries=2)
    try:
        assert client.get_json(ANN_URL, {}) == {'ok': True}
        assert [call[0] for call in calls] == ['chrome', 'chrome', 'safari17_0', 'safari17_0']
    finally:
        client.close()


@pytest.mark.parametrize('status', [400, 401, 404, 408, 422])
def test_other_4xx_never_retry_or_switch_profile(wire, status):
    replies, calls, _ = wire
    replies.append(response(status))
    client = BSEClient(rate_delay=0)
    try:
        with pytest.raises(BSEUnavailableError, match=f'HTTP {status}'):
            client.get_json(ANN_URL, {})
        assert [call[0] for call in calls] == ['chrome']
    finally:
        client.close()


def test_curl_transport_error_is_wrapped_without_retry_or_fallback(wire):
    replies, calls, _ = wire
    replies.append(curl_requests.exceptions.ConnectionError('connection failed'))
    client = BSEClient(rate_delay=0)
    try:
        with pytest.raises(BSEUnavailableError, match='ConnectionError: connection failed'):
            client.get_json(ANN_URL, {})
        assert len(calls) == 1
    finally:
        client.close()


def test_mock_transport_never_opens_a_curl_session(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('injected transport must stay offline')
    monkeypatch.setattr(curl_requests, 'Session', forbidden)
    client = BSEClient(transport=httpx.MockTransport(
        lambda req: httpx.Response(200, json={'offline': True})), rate_delay=0)
    try:
        assert client.get_json(ANN_URL, {}) == {'offline': True}
    finally:
        client.close()


def test_resolver_and_all_fetcher_routes_use_the_curl_seam(wire):
    replies, calls, _ = wire
    replies.extend([
        response(body=b"<li class='quotemenuselect' onclick=\"liclick('509631','HEG Ltd')\"></li>"),
        response(body=b'{"Table": []}'),
        response(body=json.dumps({'Table': [{'Year': '2026', 'PDFDownload':
            'https://www.bseindia.com/bseplus/AnnualReport/509631/5096312026.pdf'}]}).encode()),
        response(404), response(body=b'%PDF-1.4 live'), response(body=b'%PDF-1.4 archive'),
    ])
    client = BSEClient(rate_delay=0)
    try:
        assert resolve('HEG', client)[0].scrip_code == '509631'
        assert list_filings('509631', [], 1, client, everything=True) == []
        archived = list_annual_reports('509631', client)
        filing = Filing(news_id='test', date='2026-09-30', headline='HEG', attachment='notice.pdf',
                        folder='quarterly', category='Results')
        assert download_filing(filing, client) == b'%PDF-1.4 live'
        assert download_filing(archived[0], client) == b'%PDF-1.4 archive'
        assert [call[1] for call in calls] == [URL, ANN_URL, AR_URL,
            'https://www.bseindia.com/xml-data/corpfiling/AttachHis/notice.pdf',
            'https://www.bseindia.com/xml-data/corpfiling/AttachLive/notice.pdf', archived[0].attachment]
    finally:
        client.close()


def test_rate_delay_applies_to_fallback_and_retry_requests(wire, monkeypatch):
    replies, calls, _ = wire
    replies.extend([response(403, BLOCK), response(503), response()])
    sleeps = []
    monkeypatch.setattr('engine.bse_client.time.sleep', sleeps.append)
    client = BSEClient(rate_delay=0.3, retry_backoff=0.5)
    try:
        assert client.get_json(ANN_URL, {}) == {'ok': True}
        assert sleeps.count(0.3) == len(calls) == 3
        assert 0.5 in sleeps
    finally:
        client.close()
