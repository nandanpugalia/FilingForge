from datetime import date
from importlib import import_module
from io import BytesIO

import pytest
from pypdf import PdfWriter
from pypdf.generic import RectangleObject

from spike.linked_document.models import DocumentContext, PdfEvidence


def context(folder: str = "annual-reports") -> DocumentContext:
    return DocumentContext(
        company="Example Limited",
        folder=folder,
        filing_date=date(2026, 7, 28),
        headline="Annual Report FY 2025-26",
        source_url="https://www.bseindia.com/example.pdf",
    )


def cover_evidence(*, pages: int = 2, links: tuple[str, ...] | None = None) -> PdfEvidence:
    return PdfEvidence(
        page_count=pages,
        text=(
            "BSE Limited. Pursuant to Regulation 34, please note that the requested "
            "document has been uploaded and is available at the following web-link."
        ),
        links=links if links is not None else ("https://investor.example.com/document.pdf",),
    )


@pytest.mark.parametrize("folder", ["annual-reports", "concalls", "investor-ppts", "quarterly"])
def test_detects_link_only_cover_letter_in_supported_folder(folder):
    evidence = import_module("spike.linked_document.evidence")

    assert evidence.is_linked_cover_letter(context(folder), cover_evidence()) is True


def test_rejects_same_letter_in_arbitrary_folder():
    evidence = import_module("spike.linked_document.evidence")

    assert evidence.is_linked_cover_letter(context("press"), cover_evidence()) is False


def test_rejects_short_pdf_without_external_https_link():
    evidence = import_module("spike.linked_document.evidence")

    assert evidence.is_linked_cover_letter(context(), cover_evidence(links=())) is False
    assert evidence.is_linked_cover_letter(
        context(), cover_evidence(links=("http://investor.example.com/document.pdf",))
    ) is False


def test_rejects_short_genuine_transcript_without_delegation_language():
    evidence = import_module("spike.linked_document.evidence")
    transcript = PdfEvidence(
        page_count=2,
        text="Moderator: Good afternoon. Analyst: Could you discuss margins? CFO: Certainly.",
        links=(),
    )

    assert evidence.is_linked_cover_letter(context("concalls"), transcript) is False


def test_rejects_long_document_even_if_it_contains_cover_signals():
    evidence = import_module("spike.linked_document.evidence")

    assert evidence.is_linked_cover_letter(context(), cover_evidence(pages=4)) is False


def test_extracts_page_count_and_uri_annotation_from_pdf():
    evidence = import_module("spike.linked_document.evidence")
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_blank_page(width=200, height=200)
    writer.add_uri(
        page_number=0,
        uri="https://investor.example.com/report.pdf",
        rect=RectangleObject((0, 0, 20, 20)),
    )
    output = BytesIO()
    writer.write(output)

    extracted = evidence.extract_pdf_evidence(output.getvalue())

    assert extracted.page_count == 2
    assert extracted.links == ("https://investor.example.com/report.pdf",)
