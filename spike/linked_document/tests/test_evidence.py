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


def test_external_links_drop_truncated_prefix_duplicate():
    evidence = import_module("spike.linked_document.evidence")
    extracted = PdfEvidence(
        page_count=1,
        text="",
        links=(
            "https://investor.kfintech.com/annual-reports/",
            "https://investor.kfintech.com/annual",
        ),
    )

    assert evidence.external_https_links(extracted) == (
        "https://investor.kfintech.com/annual-reports/",
    )


def test_reconstructs_a_visible_https_url_wrapped_at_path_hyphens():
    evidence = import_module("spike.linked_document.evidence")
    text = """The presentation is available at:
https://www.hdfcbank.com/content/repositories/723fb80a-
7ae1be57/?path=/Investor/pdf/Q4FY25-
Earnings-Presentation.pdf
This is for your information.
"""

    assert evidence.visible_https_links(text) == (
        "https://www.hdfcbank.com/content/repositories/723fb80a-7ae1be57/"
        "?path=/Investor/pdf/Q4FY25-Earnings-Presentation.pdf",
    )


def test_unwraps_outlook_safe_link_before_removing_generic_homepage():
    evidence = import_module("spike.linked_document.evidence")
    target = "https://www.adanienterprises.com/investors/Q4-FY25-Transcript.pdf"
    safe_link = (
        "https://ind01.safelinks.protection.outlook.com/"
        "?url=https%3A%2F%2Fwww.adanienterprises.com%2Finvestors%2FQ4-FY25-Transcript.pdf"
        "&data=public-wrapper-metadata"
    )
    extracted = PdfEvidence(
        page_count=1,
        text="",
        links=(safe_link, "https://www.adanienterprises.com/"),
    )

    assert evidence.external_https_links(extracted) == (target,)
