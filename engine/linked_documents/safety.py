from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable, Iterable
from typing import Literal
from urllib.parse import urljoin, urlsplit

import httpx

from .models import HttpDocument

HTML_MAX_BYTES = 3 * 1024 * 1024
PDF_MAX_BYTES = 100 * 1024 * 1024
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_USER_AGENT = "FilingForge/0.1 linked-document"


class UnsafeUrl(ValueError):
    pass


class ResponseTooLarge(ValueError):
    pass


class TooManyRedirects(ValueError):
    pass


def resolve_host(host: str) -> tuple[str, ...]:
    addresses = {item[4][0] for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)}
    return tuple(sorted(addresses))


def validate_public_https_url(
    url: str,
    *,
    resolve: Callable[[str], Iterable[str]] = resolve_host,
) -> str:
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise UnsafeUrl("malformed URL") from exc

    if parsed.scheme.lower() != "https":
        raise UnsafeUrl("only HTTPS is allowed")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeUrl("credentials are not allowed in URLs")
    if not host:
        raise UnsafeUrl("hostname is required")
    if port not in (None, 443):
        raise UnsafeUrl("only the standard HTTPS port is allowed")

    normalized_host = host.lower().rstrip(".")
    if normalized_host == "localhost" or normalized_host.endswith((".localhost", ".local")):
        raise UnsafeUrl("local hostnames are not allowed")

    try:
        literal = ipaddress.ip_address(normalized_host)
    except ValueError:
        try:
            addresses = tuple(resolve(normalized_host))
        except OSError as exc:
            raise UnsafeUrl("hostname could not be resolved") from exc
        if not addresses:
            raise UnsafeUrl("hostname did not resolve")
    else:
        addresses = (str(literal),)

    for address in addresses:
        try:
            parsed_address = ipaddress.ip_address(address)
        except ValueError as exc:
            raise UnsafeUrl("resolver returned an invalid address") from exc
        if (
            not parsed_address.is_global
            or parsed_address.is_multicast
            or parsed_address.is_reserved
            or parsed_address.is_unspecified
        ):
            raise UnsafeUrl("hostname resolves to a non-public address")
    return url


def fetch_public_document(
    client: httpx.Client,
    url: str,
    *,
    expected: Literal["html", "pdf", "json"],
    max_redirects: int = 3,
    resolve: Callable[[str], Iterable[str]] = resolve_host,
) -> HttpDocument:
    current = url
    maximum = PDF_MAX_BYTES if expected == "pdf" else HTML_MAX_BYTES

    for redirect_count in range(max_redirects + 1):
        validate_public_https_url(current, resolve=resolve)
        request = client.build_request("GET", current, headers={"User-Agent": _USER_AGENT})
        response = client.send(request, stream=True)
        try:
            if response.status_code in _REDIRECT_STATUSES:
                location = response.headers.get("Location")
                if not location:
                    response.raise_for_status()
                if redirect_count == max_redirects:
                    raise TooManyRedirects(f"more than {max_redirects} redirects")
                current = urljoin(current, location)
                continue

            response.raise_for_status()
            declared = response.headers.get("Content-Length")
            if declared is not None and int(declared) > maximum:
                raise ResponseTooLarge(f"response exceeds {maximum} bytes")

            body = bytearray()
            for chunk in response.iter_bytes(chunk_size=64 * 1024):
                body.extend(chunk)
                if len(body) > maximum:
                    raise ResponseTooLarge(f"response exceeds {maximum} bytes")
            return HttpDocument(
                url=str(response.url),
                content_type=response.headers.get("Content-Type", "").split(";", 1)[0].lower(),
                body=bytes(body),
            )
        finally:
            response.close()

    raise TooManyRedirects(f"more than {max_redirects} redirects")
