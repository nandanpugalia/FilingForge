from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal


@dataclass(frozen=True)
class DocumentContext:
    company: str
    folder: str
    filing_date: date
    headline: str
    source_url: str


@dataclass(frozen=True)
class PdfEvidence:
    page_count: int
    text: str
    links: tuple[str, ...]


@dataclass(frozen=True)
class Candidate:
    url: str
    label: str
    source: Literal["cover", "html", "adapter"]


@dataclass(frozen=True)
class HttpDocument:
    url: str
    content_type: str
    body: bytes


@dataclass(frozen=True)
class Resolution:
    status: Literal["substantive", "resolved", "unresolved"]
    reason: str
    source_url: str | None = None
    action_url: str | None = None
    pdf: bytes | None = None
