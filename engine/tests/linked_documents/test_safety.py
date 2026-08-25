from importlib import import_module

import httpx
import pytest


def public_dns(_host: str) -> tuple[str, ...]:
    return ("93.184.216.34",)


def test_accepts_public_https_hostname():
    safety = import_module("engine.linked_documents.safety")

    assert safety.validate_public_https_url(
        "https://investor.example.com/reports/annual.pdf", resolve=public_dns
    ) == "https://investor.example.com/reports/annual.pdf"


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/report.pdf",
        "https://user:secret@example.com/report.pdf",
        "https://localhost/report.pdf",
        "https://company.local/report.pdf",
        "https://127.0.0.1/report.pdf",
        "https://10.20.30.40/report.pdf",
        "https://169.254.1.2/report.pdf",
        "https://224.0.0.1/report.pdf",
        "https://[::1]/report.pdf",
        "https://[fc00::1]/report.pdf",
    ],
)
def test_rejects_unsafe_url_shapes(url):
    safety = import_module("engine.linked_documents.safety")

    with pytest.raises(safety.UnsafeUrl):
        safety.validate_public_https_url(url, resolve=public_dns)


def test_rejects_hostname_that_resolves_to_private_address():
    safety = import_module("engine.linked_documents.safety")

    with pytest.raises(safety.UnsafeUrl):
        safety.validate_public_https_url("https://investor.example.com/report.pdf", resolve=lambda _: ("192.168.1.8",))


def test_validates_every_redirect_and_stops_after_three():
    safety = import_module("engine.linked_documents.safety")

    def handler(request: httpx.Request) -> httpx.Response:
        hop = int(request.url.params.get("hop", "0"))
        return httpx.Response(302, headers={"Location": f"https://example.com/report?hop={hop + 1}"})

    with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
        with pytest.raises(safety.TooManyRedirects):
            safety.fetch_public_document(
                client,
                "https://example.com/report?hop=0",
                expected="html",
                resolve=public_dns,
            )


@pytest.mark.parametrize(
    ("expected", "declared_size"),
    [("html", 3 * 1024 * 1024 + 1), ("pdf", 100 * 1024 * 1024 + 1)],
)
def test_rejects_declared_oversized_response(expected, declared_size):
    safety = import_module("engine.linked_documents.safety")

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Length": str(declared_size)}, content=b"small")

    with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
        with pytest.raises(safety.ResponseTooLarge):
            safety.fetch_public_document(
                client,
                "https://example.com/report",
                expected=expected,
                resolve=public_dns,
            )


def test_fetches_a_bounded_public_response():
    safety = import_module("engine.linked_documents.safety")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["User-Agent"].startswith("FilingForge/")
        return httpx.Response(200, headers={"Content-Type": "text/html"}, content=b"<html>ok</html>")

    with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
        document = safety.fetch_public_document(
            client,
            "https://example.com/reports",
            expected="html",
            resolve=public_dns,
        )

    assert document.url == "https://example.com/reports"
    assert document.content_type == "text/html"
    assert document.body == b"<html>ok</html>"
