from __future__ import annotations

import json
from collections.abc import Callable
from typing import Literal
from urllib.parse import parse_qs, urlsplit

import httpx
from pypdf.errors import PdfReadError

from .adapters import adapter_request, parse_adapter_candidates
from .candidates import parse_html_candidates, select_unique_candidate
from .evidence import external_https_links, extract_pdf_evidence, is_linked_cover_letter
from .models import DocumentContext, HttpDocument, Resolution
from .safety import UnsafeUrl, validate_public_https_url

Fetch = Callable[[str, Literal["html", "pdf", "json"]], HttpDocument]
Validate = Callable[[str], str]


def resolve_document(
    context: DocumentContext,
    original_pdf: bytes,
    *,
    fetch: Fetch,
    validate: Validate = validate_public_https_url,
) -> Resolution:
    try:
        original_evidence = extract_pdf_evidence(original_pdf)
    except (PdfReadError, ValueError, OSError) as exc:
        return Resolution(status="unresolved", reason=f"original PDF is unreadable: {type(exc).__name__}")

    if not is_linked_cover_letter(context, original_evidence):
        return Resolution(
            status="substantive",
            reason="original BSE attachment is substantive",
            source_url=context.source_url,
            pdf=original_pdf,
        )

    links = external_https_links(original_evidence)
    if len(links) != 1:
        return Resolution(status="unresolved", reason="cover letter does not contain one unique external link")
    landing_url = links[0]
    try:
        validate(landing_url)
    except UnsafeUrl as exc:
        return Resolution(status="unresolved", reason=f"unsafe external link: {exc}")

    if _looks_like_pdf(landing_url):
        return _fetch_and_validate_pdf(context, landing_url, fetch)

    try:
        adapter = adapter_request(landing_url)
        if adapter is not None:
            request_url, expected = adapter
            validate(request_url)
            landing = fetch(request_url, expected)
            hostname = (urlsplit(landing_url).hostname or "").lower().rstrip(".")
            choices = parse_adapter_candidates(hostname, landing)
        else:
            landing = fetch(landing_url, "html")
            choices = parse_html_candidates(landing.body, landing.url)
    except UnsafeUrl as exc:
        return Resolution(status="unresolved", reason=f"unsafe landing resource: {exc}", action_url=landing_url)
    except (httpx.HTTPError, json.JSONDecodeError, KeyError, ValueError) as exc:
        return Resolution(status="unresolved", reason=f"landing resource could not be read: {type(exc).__name__}", action_url=landing_url)

    selected = select_unique_candidate(context, original_evidence.text, choices)
    if selected is None:
        return Resolution(
            status="unresolved",
            reason="could not select one unique replacement PDF",
            action_url=landing_url,
        )
    try:
        validate(selected.url)
    except UnsafeUrl as exc:
        return Resolution(status="unresolved", reason=f"unsafe replacement link: {exc}", action_url=landing_url)
    return _fetch_and_validate_pdf(context, selected.url, fetch)


def _fetch_and_validate_pdf(context: DocumentContext, url: str, fetch: Fetch) -> Resolution:
    try:
        document = fetch(url, "pdf")
    except (httpx.HTTPError, ValueError) as exc:
        return Resolution(status="unresolved", reason=f"replacement download failed: {type(exc).__name__}", action_url=url)
    if not document.body.startswith(b"%PDF-"):
        return Resolution(status="unresolved", reason="replacement is not a PDF", action_url=url)
    try:
        replacement_evidence = extract_pdf_evidence(document.body)
    except (PdfReadError, ValueError, OSError) as exc:
        return Resolution(status="unresolved", reason=f"replacement PDF is unreadable: {type(exc).__name__}", action_url=url)
    if is_linked_cover_letter(context, replacement_evidence):
        return Resolution(status="unresolved", reason="replacement is another cover letter", action_url=url)
    return Resolution(
        status="resolved",
        reason="resolved substantive PDF from issuer website",
        source_url=document.url,
        pdf=document.body,
    )


def _looks_like_pdf(url: str) -> bool:
    parsed = urlsplit(url)
    if parsed.path.lower().endswith(".pdf"):
        return True
    return any(
        value.lower().endswith(".pdf")
        for values in parse_qs(parsed.query).values()
        for value in values
    )
