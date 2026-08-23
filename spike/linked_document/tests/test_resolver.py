from datetime import date
from importlib import import_module
from io import BytesIO
from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, RectangleObject

from spike.linked_document.models import DocumentContext, HttpDocument

MARUTI_FIXTURE = Path(__file__).parent / "fixtures" / "maruti_documents.json"


def make_pdf(text: str = "", *, pages: int = 1, links: tuple[str, ...] = ()) -> bytes:
    writer = PdfWriter()
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)
    for index in range(pages):
        page = writer.add_blank_page(width=612, height=792)
        if index == 0 and text:
            escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream = DecodedStreamObject()
            stream.set_data(f"BT /F1 10 Tf 40 740 Td ({escaped}) Tj ET".encode("latin-1"))
            page[NameObject("/Resources")] = DictionaryObject(
                {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
            )
            page[NameObject("/Contents")] = writer._add_object(stream)
    for link in links:
        writer.add_uri(0, link, RectangleObject((0, 0, 40, 20)))
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def context(
    folder: str = "annual-reports",
    headline: str = "Annual Report FY 2025-26",
) -> DocumentContext:
    return DocumentContext(
        company="Example Limited",
        folder=folder,
        filing_date=date(2026, 7, 28),
        headline=headline,
        source_url="https://www.bseindia.com/original.pdf",
    )


def cover_pdf(link: str, text: str | None = None) -> bytes:
    return make_pdf(
        text
        or "BSE Limited pursuant to Regulation 34 Annual Report FY 2025-26 is available at the following link",
        pages=2,
        links=(link,),
    )


def fake_fetch(documents: dict[str, HttpDocument]):
    calls: list[tuple[str, str]] = []

    def fetch(url: str, expected: str) -> HttpDocument:
        calls.append((url, expected))
        return documents[url]

    return fetch, calls


def allow_public(url: str) -> str:
    return url


def test_substantive_original_returns_without_external_fetch():
    resolver = import_module("spike.linked_document.resolver")
    fetch, calls = fake_fetch({})
    original = make_pdf("A complete annual report", pages=4)

    result = resolver.resolve_document(context(), original, fetch=fetch, validate=allow_public)

    assert result.status == "substantive"
    assert result.pdf == original
    assert calls == []


def test_resolves_direct_link_to_substantive_pdf_in_one_request():
    resolver = import_module("spike.linked_document.resolver")
    target = "https://investor.example.com/Annual_Report_FY_2025-26.pdf"
    replacement = make_pdf("Complete annual report", pages=10)
    fetch, calls = fake_fetch({target: HttpDocument(target, "application/pdf", replacement)})

    result = resolver.resolve_document(
        context(), cover_pdf(target), fetch=fetch, validate=allow_public
    )

    assert result.status == "resolved"
    assert result.pdf == replacement
    assert calls == [(target, "pdf")]


def test_prefers_one_direct_pdf_over_generic_homepage_link():
    resolver = import_module("spike.linked_document.resolver")
    target = "https://investor.example.com/Transcript_Q1FY27.pdf"
    homepage = "https://investor.example.com/"
    replacement = make_pdf("Moderator Analyst Management transcript", pages=10)
    original = make_pdf(
        "BSE Limited pursuant to Regulation transcript is available at the following link",
        pages=1,
        links=(target, homepage),
    )
    fetch, calls = fake_fetch({target: HttpDocument(target, "application/pdf", replacement)})

    result = resolver.resolve_document(
        context("concalls", "Earnings Call Transcript Q1 FY2026-27"),
        original,
        fetch=fetch,
        validate=allow_public,
    )

    assert result.status == "resolved"
    assert calls == [(target, "pdf")]


def test_resolves_static_landing_page_then_substantive_pdf():
    resolver = import_module("spike.linked_document.resolver")
    landing = "https://investor.example.com/annual-reports/"
    target = "https://investor.example.com/reports/Annual_Report_FY_2025-26.pdf"
    replacement = make_pdf("Complete annual report", pages=10)
    html = b'<a href="/reports/Annual_Report_FY_2025-26.pdf">Annual Report FY 2025-26</a>'
    fetch, calls = fake_fetch(
        {
            landing: HttpDocument(landing, "text/html", html),
            target: HttpDocument(target, "application/pdf", replacement),
        }
    )

    result = resolver.resolve_document(
        context(), cover_pdf(landing), fetch=fetch, validate=allow_public
    )

    assert result.status == "resolved"
    assert result.source_url == target
    assert calls == [(landing, "html"), (target, "pdf")]


def test_resolves_maruti_through_public_json_adapter():
    resolver = import_module("spike.linked_document.resolver")
    adapters = import_module("spike.linked_document.adapters")
    landing = "https://www.marutisuzuki.com/corporate/investors/company-reports"
    target = (
        "https://prod-nexa.marutisuzuki.com/content/dam/arena-eds/corporate/pdf/"
        "company-reports/2025-2026/Transcript_earnings_call_Maruti_Suzuki_Q4_FY_26.pdf"
    )
    replacement = make_pdf("Moderator Analyst Management transcript", pages=15)
    fetch, calls = fake_fetch(
        {
            adapters.MARUTI_DOCUMENTS_URL: HttpDocument(
                adapters.MARUTI_DOCUMENTS_URL, "application/json", MARUTI_FIXTURE.read_bytes()
            ),
            target: HttpDocument(target, "application/pdf", replacement),
        }
    )
    original = cover_pdf(
        landing,
        "BSE Limited pursuant to Regulation Earnings Call Transcript for the quarter and year ended March 31, 2026 can be accessed at the following link",
    )

    result = resolver.resolve_document(
        context("concalls", "Earnings Call Transcript"),
        original,
        fetch=fetch,
        validate=allow_public,
    )

    assert result.status == "resolved"
    assert result.source_url == target
    assert calls == [(adapters.MARUTI_DOCUMENTS_URL, "json"), (target, "pdf")]


def test_rejects_replacement_that_is_another_cover_letter():
    resolver = import_module("spike.linked_document.resolver")
    target = "https://investor.example.com/Annual_Report_FY_2025-26.pdf"
    replacement = cover_pdf("https://investor.example.com/another-page")
    fetch, _calls = fake_fetch({target: HttpDocument(target, "application/pdf", replacement)})

    result = resolver.resolve_document(
        context(), cover_pdf(target), fetch=fetch, validate=allow_public
    )

    assert result.status == "unresolved"
    assert "cover letter" in result.reason


def test_rejects_non_pdf_candidate_response():
    resolver = import_module("spike.linked_document.resolver")
    target = "https://investor.example.com/Annual_Report_FY_2025-26.pdf"
    fetch, _calls = fake_fetch({target: HttpDocument(target, "text/html", b"<html>not PDF</html>")})

    result = resolver.resolve_document(
        context(), cover_pdf(target), fetch=fetch, validate=allow_public
    )

    assert result.status == "unresolved"
    assert "not a PDF" in result.reason


def test_ambiguous_static_candidates_do_not_trigger_pdf_download():
    resolver = import_module("spike.linked_document.resolver")
    landing = "https://investor.example.com/annual-reports/"
    html = b"""
      <a href="/a/Annual_Report_FY_2025-26.pdf">Annual Report FY 2025-26</a>
      <a href="/b/Annual_Report_FY_2025-26.pdf">Annual Report FY 2025-26</a>
    """
    fetch, calls = fake_fetch({landing: HttpDocument(landing, "text/html", html)})

    result = resolver.resolve_document(
        context(), cover_pdf(landing), fetch=fetch, validate=allow_public
    )

    assert result.status == "unresolved"
    assert "unique" in result.reason
    assert calls == [(landing, "html")]


def test_unsafe_cover_link_is_unresolved_without_fetch():
    resolver = import_module("spike.linked_document.resolver")
    fetch, calls = fake_fetch({})

    result = resolver.resolve_document(
        context(), cover_pdf("https://127.0.0.1/report.pdf"), fetch=fetch
    )

    assert result.status == "unresolved"
    assert "unsafe" in result.reason
    assert calls == []
