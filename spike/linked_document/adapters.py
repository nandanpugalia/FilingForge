from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from urllib.parse import urlsplit

from .models import Candidate, HttpDocument

MARUTI_DOCUMENTS_URL = (
    "https://www.marutisuzuki.com/graphql/execute.json/msil-platform/"
    "corporateDocumentsList;documentCategory=companyReports"
)


def maruti_candidates(document: HttpDocument) -> tuple[Candidate, ...]:
    payload = json.loads(document.body)
    items = payload["data"]["corporateDocumentsList"]["items"]
    candidates: list[Candidate] = []
    for item in items:
        pdf_link = item.get("pdfLink")
        if isinstance(pdf_link, dict):
            url = pdf_link.get("_publishUrl") or pdf_link.get("_path")
        else:
            url = pdf_link
        if not isinstance(url, str) or not url.startswith("https://"):
            continue

        description = item.get("description")
        if isinstance(description, dict):
            description_text = description.get("markdown") or description.get("html") or ""
        else:
            description_text = description or ""
        label = " ".join(
            str(value).strip()
            for value in (
                item.get("title"),
                description_text,
                item.get("yearRange"),
                item.get("date"),
            )
            if value
        )
        candidates.append(Candidate(url=url, label=label, source="adapter"))
    return tuple(candidates)


ADAPTERS: Mapping[str, Callable[[HttpDocument], tuple[Candidate, ...]]] = {
    "www.marutisuzuki.com": maruti_candidates,
}


def adapter_request(landing_url: str) -> tuple[str, str] | None:
    hostname = (urlsplit(landing_url).hostname or "").lower().rstrip(".")
    if hostname == "www.marutisuzuki.com":
        return MARUTI_DOCUMENTS_URL, "json"
    return None


def parse_adapter_candidates(hostname: str, document: HttpDocument) -> tuple[Candidate, ...]:
    parser = ADAPTERS.get(hostname.lower().rstrip("."))
    if parser is None:
        return ()
    return parser(document)
