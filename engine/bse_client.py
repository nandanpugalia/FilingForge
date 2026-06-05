"""The single network seam. All BSE HTTP goes through here so every other module is pure
logic over data, and the whole suite runs offline via an injected MockTransport."""
from __future__ import annotations
import time
from typing import Optional
import httpx
from .errors import BSEUnavailableError

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.bseindia.com/",
    "Accept": "application/json, text/plain, */*",
}
RATE_DELAY = 0.3   # confirmed polite in spike (40+ reqs, zero blocks)
MAX_RETRIES = 2    # 1 initial attempt + this many retries on a transient blip
RETRY_BACKOFF = 0.5
# Transient server states worth a second try (rate-limit + the 5xx family). A 4xx is the
# caller's mistake (or a genuinely-missing file) and is never retried.
_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


class BSEClient:
    def __init__(self, transport: Optional[httpx.BaseTransport] = None, rate_delay: float = RATE_DELAY,
                 max_retries: int = MAX_RETRIES, retry_backoff: float = RETRY_BACKOFF):
        # Granular timeouts: a hung connect/read fails fast instead of freezing the app on
        # a dead socket — then the retry below gives a flaky network a second chance.
        self._client = httpx.Client(headers=HEADERS, follow_redirects=True, transport=transport,
                                    timeout=httpx.Timeout(60.0, connect=10.0))
        self._rate_delay = rate_delay
        self._max_retries = max_retries
        self._retry_backoff = retry_backoff

    def _sleep(self) -> None:
        if self._rate_delay:
            time.sleep(self._rate_delay)

    def _get(self, url: str, params: Optional[dict] = None) -> httpx.Response:
        """GET with retry on transport errors and transient 5xx/429. Returns the final
        Response (which callers interpret); raises BSEUnavailableError only if every
        attempt errored at the transport layer."""
        last_exc: Optional[Exception] = None
        for attempt in range(self._max_retries + 1):
            try:
                r = self._client.get(url, params=params) if params is not None else self._client.get(url)
            except httpx.HTTPError as e:
                last_exc = e
                if attempt < self._max_retries:
                    if self._retry_backoff:
                        time.sleep(self._retry_backoff * (attempt + 1))
                    continue
                raise BSEUnavailableError(f"{type(e).__name__}: {e}") from e
            if r.status_code in _RETRY_STATUSES and attempt < self._max_retries:
                if self._retry_backoff:
                    time.sleep(self._retry_backoff * (attempt + 1))
                continue
            return r
        raise BSEUnavailableError(str(last_exc))   # defensive; loop always returns/raises above

    def get_json(self, url: str, params: dict) -> dict:
        r = self._get(url, params)
        if not r.is_success:
            raise BSEUnavailableError(f"HTTP {r.status_code} for {url}")
        self._sleep()
        try:
            return r.json()
        except Exception as e:
            raise BSEUnavailableError(f"non-JSON from {url}: {e}") from e

    def get_text(self, url: str, params: dict) -> str:
        r = self._get(url, params)
        if not r.is_success:
            raise BSEUnavailableError(f"HTTP {r.status_code} for {url}")
        self._sleep()
        return r.text

    def get_bytes(self, url: str) -> bytes:
        r = self._get(url)
        if r.status_code >= 500 or r.status_code == 429:
            raise BSEUnavailableError(f"HTTP {r.status_code} for {url}")
        self._sleep()
        return r.content if r.status_code == 200 else b""

    def close(self) -> None:
        self._client.close()
