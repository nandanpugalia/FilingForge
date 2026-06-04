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
RATE_DELAY = 0.3   # confirmed polite in spike (40+ reqs, zero blocks); also Nazar prod default


class BSEClient:
    def __init__(self, transport: Optional[httpx.BaseTransport] = None, rate_delay: float = RATE_DELAY):
        self._client = httpx.Client(headers=HEADERS, timeout=60, follow_redirects=True,
                                    transport=transport)
        self._rate_delay = rate_delay

    def _sleep(self) -> None:
        if self._rate_delay:
            time.sleep(self._rate_delay)

    def get_json(self, url: str, params: dict) -> dict:
        try:
            r = self._client.get(url, params=params)
        except httpx.HTTPError as e:
            raise BSEUnavailableError(f"{type(e).__name__}: {e}") from e
        if r.status_code >= 500 or r.status_code == 429:
            raise BSEUnavailableError(f"HTTP {r.status_code} for {url}")
        self._sleep()
        try:
            return r.json()
        except Exception as e:
            raise BSEUnavailableError(f"non-JSON from {url}: {e}") from e

    def get_text(self, url: str, params: dict) -> str:
        try:
            r = self._client.get(url, params=params)
        except httpx.HTTPError as e:
            raise BSEUnavailableError(f"{type(e).__name__}: {e}") from e
        if r.status_code >= 500 or r.status_code == 429:
            raise BSEUnavailableError(f"HTTP {r.status_code} for {url}")
        self._sleep()
        return r.text

    def get_bytes(self, url: str) -> bytes:
        try:
            r = self._client.get(url)
        except httpx.HTTPError as e:
            raise BSEUnavailableError(f"{type(e).__name__}: {e}") from e
        self._sleep()
        return r.content if r.status_code == 200 else b""

    def close(self) -> None:
        self._client.close()
