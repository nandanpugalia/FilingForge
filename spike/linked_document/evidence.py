from __future__ import annotations

import re
from io import BytesIO
from urllib.parse import urlsplit

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
    links.extend(match.rstrip(".,;:)]}") for match in _URL_RE.findall(text))
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
    has_delegation = any(signal in normalized for signal in _DELEGATION_SIGNALS)
    has_external_link = any(_is_external_https_link(link) for link in evidence.links)
    return has_exchange_context and has_delegation and has_external_link


def external_https_links(evidence: PdfEvidence) -> tuple[str, ...]:
    return tuple(link for link in evidence.links if _is_external_https_link(link))


def _is_external_https_link(url: str) -> bool:
    parsed = urlsplit(url)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return False
    host = parsed.hostname.lower().rstrip(".")
    return not any(host == exchange or host.endswith(f".{exchange}") for exchange in _EXCHANGE_HOSTS)
