"""The single BSE network seam: browser TLS in production, injected HTTPX in tests."""
from __future__ import annotations
import os
import time
from typing import Optional

import certifi
from curl_cffi import CurlOpt, ffi, requests as curl_requests
import httpx

from .errors import BSEUnavailableError

# BSE page context, shared by both browser profiles. curl supplies the matching
# User-Agent, client hints and Accept-Encoding: hard-coded Chrome headers would
# contradict Safari's TLS/HTTP2 fingerprint on fallback.
HEADERS = {
    "Referer": "https://www.bseindia.com/",
    "Origin": "https://www.bseindia.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
}
RATE_DELAY = 0.3
MAX_RETRIES = 2    # 1 initial attempt + this many retries on 429/5xx only
RETRY_BACKOFF = 0.5


class BSEClient:
    def __init__(self, transport: Optional[httpx.BaseTransport] = None, rate_delay: float = RATE_DELAY,
                 max_retries: int = MAX_RETRIES, retry_backoff: float = RETRY_BACKOFF):
        self._transport = transport
        self._fallback_client = None
        self._rate_delay = rate_delay
        self._max_retries = max_retries
        self._retry_backoff = retry_backoff
        # Preserve custom certificate stores (file before directory) on Windows,
        # macOS and Linux. Verification remains enabled for both fingerprints.
        ca_file = os.environ.get("SSL_CERT_FILE", "")
        ca_dir = os.environ.get("SSL_CERT_DIR", "")
        self._verify = ca_file if os.path.isfile(ca_file) else certifi.where()
        self._curl_options = {}
        if not os.path.isfile(ca_file) and os.path.isdir(ca_dir):
            # Disable the default CA bundle, NOT certificate verification, so an
            # explicit trust directory does not silently acquire public roots.
            self._curl_options = {CurlOpt.CAINFO: ffi.NULL, CurlOpt.CAPATH: ca_dir}
        if transport is not None:
            self._client = httpx.Client(headers=HEADERS, follow_redirects=True, transport=transport,
                                        timeout=httpx.Timeout(30.0, connect=10.0))
        else:
            self._client = self._new_session("chrome")

    def _new_session(self, profile: str) -> curl_requests.Session:
        return curl_requests.Session(impersonate=profile, headers=HEADERS,
                                     verify=self._verify, curl_options=self._curl_options,
                                     allow_redirects=True, timeout=(10.0, 30.0))

    def _sleep(self) -> None:
        if self._rate_delay:
            time.sleep(self._rate_delay)

    def _get(self, url: str, params: Optional[dict] = None) -> httpx.Response | curl_requests.Response:
        """Start with Chrome; try Safari once on 403. Only 429/5xx spend retries.

        Separate sessions prevent Safari from reusing a Chrome TLS connection.
        An injected transport exercises the same policy without any live I/O.
        """
        client = self._client
        used_fallback = False
        retries = 0
        while True:
            self._sleep()
            try:
                r = client.get(url, params=params) if params is not None else client.get(url)
            except (httpx.HTTPError, curl_requests.exceptions.RequestException) as e:
                raise BSEUnavailableError(f"{type(e).__name__}: {e}") from e
            if r.status_code == 403:
                if not used_fallback:
                    used_fallback = True
                    if self._transport is None:
                        if self._fallback_client is None:
                            self._fallback_client = self._new_session("safari17_0")
                        client = self._fallback_client
                    continue
                detail = " (fingerprint block: Akamai Access Denied)" if "access denied" in r.text.lower() else ""
                raise BSEUnavailableError(f"HTTP 403 for {url}{detail}")
            if (r.status_code == 429 or 500 <= r.status_code < 600) and retries < self._max_retries:
                retries += 1
                if self._retry_backoff:
                    time.sleep(self._retry_backoff * retries)
                continue
            return r

    def get_json(self, url: str, params: dict) -> dict:
        r = self._get(url, params)
        if not 200 <= r.status_code < 300:
            raise BSEUnavailableError(f"HTTP {r.status_code} for {url}")
        try:
            return r.json()
        except Exception as e:
            raise BSEUnavailableError(f"non-JSON from {url}: {e}") from e

    def get_text(self, url: str, params: dict) -> str:
        r = self._get(url, params)
        if not 200 <= r.status_code < 300:
            raise BSEUnavailableError(f"HTTP {r.status_code} for {url}")
        return r.text

    def get_bytes(self, url: str) -> bytes:
        r = self._get(url)
        if r.status_code >= 500 or r.status_code == 429:
            raise BSEUnavailableError(f"HTTP {r.status_code} for {url}")
        return r.content if r.status_code == 200 else b""

    def close(self) -> None:
        self._client.close()
        if self._fallback_client is not None:
            self._fallback_client.close()
