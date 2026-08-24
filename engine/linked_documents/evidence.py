from __future__ import annotations

import re
from io import BytesIO
from urllib.parse import parse_qs, urlsplit

from pypdf import PdfReader

from .models import DocumentContext, PdfEvidence

SUPPORTED_FOLDERS = frozenset({"annual-reports", "concalls", "investor-ppts", "quarterly"})
_EXCHANGE_SIGNALS = (
    "bse",
    "nse",
    "stock exchange",
    "listing regulation",
    "pursuant to regulation",
    "please find enclosed",
)
_DELEGATION_SIGNALS = (
    "available at",
    "available on",
    "can be accessed",
    "may be accessed",
    "uploaded on",
    "web-link",
    "weblink",
    "following link",
    "link below",
)
_URL_RE = re.compile(r"https://[^\s<>()\"'\]]+", re.IGNORECASE)
_URL_CONTINUATION_RE = re.compile(r"[A-Za-z0-9%/?=&._~:+-]+")
_EXCHANGE_HOSTS = ("bseindia.com", "nseindia.com")
_MAX_TEXT_CHARS = 30_000


def extract_pdf_evidence(pdf: bytes, *, max_pages: int = 4) -> PdfEvidence:
    reader = PdfReader(BytesIO(pdf))
    text_parts: list[str] = []
    links: list[str] = []

    for page in reader.pages[:max_pages]:
        text_parts.append(page.extract_text() or "")
        for annotation_ref in page.get("/Annots", ()):  # type: ignore[union-attr]
            annotation = annotation_ref.get_object()
            action_ref = annotation.get("/A")
            if action_ref is None:
                continue
            action = action_ref.get_object() if hasattr(action_ref, "get_object") else action_ref
            uri = action.get("/URI")
            if uri:
                links.append(str(uri))

    text = "\n".join(text_parts)[:_MAX_TEXT_CHARS]
    links.extend(visible_https_links(text))
    return PdfEvidence(
        page_count=len(reader.pages),
        text=text,
        links=tuple(dict.fromkeys(links)),
    )


def is_linked_cover_letter(context: DocumentContext, evidence: PdfEvidence) -> bool:
    if context.folder not in SUPPORTED_FOLDERS or not 1 <= evidence.page_count <= 3:
        return False

    normalized = " ".join(evidence.text.lower().split())
    has_exchange_context = any(signal in normalized for signal in _EXCHANGE_SIGNALS)
    has_external_link = any(_is_external_https_link(link) for link in evidence.links)
    has_website = "website" in normalized or "web site" in normalized
    has_availability = any(word in normalized for word in ("uploaded", "available", "accessed"))
    has_strong_delegation = has_website and has_availability and (
        "link" in normalized or has_external_link
    )
    has_delegation = any(signal in normalized for signal in _DELEGATION_SIGNALS) or has_strong_delegation
    has_locator_evidence = has_external_link or (has_strong_delegation and "link" in normalized)
    return has_exchange_context and has_delegation and has_locator_evidence


def external_https_links(evidence: PdfEvidence) -> tuple[str, ...]:
    links = tuple(
        dict.fromkeys(
            _unwrap_safe_link(link)
            for link in evidence.links
            if _is_external_https_link(link)
        )
    )
    return tuple(
        link
        for link in links
        if not any(other != link and other.startswith(link) for other in links)
    )


def visible_https_links(text: str) -> tuple[str, ...]:
    lines = text.splitlines()
    links: list[str] = []
    for index, line in enumerate(lines):
        for match in _URL_RE.findall(line):
            url = match.rstrip(".,;:)]}")
            next_index = index + 1
            while url.endswith("-") and next_index < len(lines):
                continuation = lines[next_index].strip()
                if not _URL_CONTINUATION_RE.fullmatch(continuation):
                    break
                url += continuation.rstrip(".,;:)]}")
                next_index += 1
            links.append(url)
    return tuple(dict.fromkeys(links))


def _unwrap_safe_link(url: str) -> str:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if host == "safelinks.protection.outlook.com" or host.endswith(".safelinks.protection.outlook.com"):
        embedded = parse_qs(parsed.query).get("url", [None])[0]
        if isinstance(embedded, str) and _is_external_https_link(embedded):
            return embedded
    return url


def _is_external_https_link(url: str) -> bool:
    parsed = urlsplit(url)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return False
    host = parsed.hostname.lower().rstrip(".")
    return not any(host == exchange or host.endswith(f".{exchange}") for exchange in _EXCHANGE_HOSTS)
