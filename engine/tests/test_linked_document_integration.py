from io import BytesIO

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, RectangleObject

import engine.library as library
from engine.linked_documents.models import HttpDocument
from engine.models import CURATED_BY_KEY, Filing
from engine.pending import list_pending


AR = CURATED_BY_KEY["annual_report"]


def make_pdf(text: str = "Complete annual report with substantive financial discussion", *,
             pages: int = 4, link: str | None = None) -> bytes:
    writer = PdfWriter()
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    font_ref = writer._add_object(font)
    for index in range(pages):
        page = writer.add_blank_page(width=612, height=792)
        if index == 0:
            escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream = DecodedStreamObject()
            stream.set_data(f"BT /F1 10 Tf 40 740 Td ({escaped}) Tj ET".encode("latin-1"))
            page[NameObject("/Resources")] = DictionaryObject(
                {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
            )
            page[NameObject("/Contents")] = writer._add_object(stream)
    if link:
        writer.add_uri(0, link, RectangleObject((0, 0, 40, 20)))
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def filing(news_id: str = "news-1", *, attachment: str = "notice.pdf") -> Filing:
    return Filing(
        news_id=news_id,
        date="2026-07-28",
        headline="Annual Report FY 2025-26",
        attachment=attachment,
        folder="annual-reports",
        category="Annual Reports",
    )


def cover(link: str | None) -> bytes:
    return make_pdf(
        "BSE Limited pursuant to Regulation Annual Report FY 2025-26 "
        "is available on the company website at the following link",
        pages=2,
        link=link,
    )


def arrange(monkeypatch, filings: list[Filing], pdfs: dict[str, bytes]) -> None:
    monkeypatch.setattr(library, "list_all_filings", lambda *_args, **_kwargs: filings)
    monkeypatch.setattr(library, "download_filing", lambda f, _client: pdfs[f.news_id])


def allow_public(url: str) -> str:
    return url


def test_substantive_bse_pdf_is_saved_without_issuer_request(tmp_path, monkeypatch):
    f = filing()
    arrange(monkeypatch, [f], {f.news_id: make_pdf()})
    calls = []

    def issuer_fetch(url, expected):
        calls.append((url, expected))
        raise AssertionError("normal document must not fetch issuer website")

    result = library.build_library(
        "543210", "KFINTECH", tmp_path, [AR], 2, object(),
        issuer_fetch=issuer_fetch, link_validator=allow_public,
    )

    assert result.downloaded == ["news-1"]
    assert result.pending == []
    assert calls == []


def test_cover_with_unique_direct_pdf_saves_replacement_under_original_identity(tmp_path, monkeypatch):
    f = filing()
    target = "https://investor.example.com/Annual_Report_FY_2025-26.pdf"
    replacement = make_pdf("Full issuer annual report", pages=10)
    arrange(monkeypatch, [f], {f.news_id: cover(target)})
    calls = []

    def issuer_fetch(url, expected):
        calls.append((url, expected))
        return HttpDocument(url, "application/pdf", replacement)

    result = library.build_library(
        "543210", "KFINTECH", tmp_path, [AR], 2, object(),
        issuer_fetch=issuer_fetch, link_validator=allow_public,
    )

    company = tmp_path / "KFINTECH"
    saved = next((company / "annual-reports").rglob("*.pdf"))
    assert result.downloaded == ["news-1"]
    assert result.pending == []
    assert saved.read_bytes() == replacement
    assert saved.name.endswith("__news-1.pdf")
    assert "news_id: news-1" in saved.with_suffix(".md").read_text(encoding="utf-8")
    assert calls == [(target, "pdf")]


def test_ambiguous_issuer_page_creates_pending_slot_without_library_document(tmp_path, monkeypatch):
    f = filing()
    landing = "https://investor.example.com/annual-reports/"
    arrange(monkeypatch, [f], {f.news_id: cover(landing)})
    html = b"""
      <a href="/a/Annual_Report_FY_2025-26.pdf">Annual Report FY 2025-26</a>
      <a href="/b/Annual_Report_FY_2025-26.pdf">Annual Report FY 2025-26</a>
    """

    def issuer_fetch(url, expected):
        return HttpDocument(url, "text/html", html)

    result = library.build_library(
        "543210", "KFINTECH", tmp_path, [AR], 2, object(),
        issuer_fetch=issuer_fetch, link_validator=allow_public,
    )

    company = tmp_path / "KFINTECH"
    assert result.downloaded == []
    assert result.failed == []
    assert len(result.pending) == 1
    assert result.pending[0].issuer_url == landing
    assert result.pending[0].expected_period == "FY 2025-26"
    assert list_pending(company) == result.pending
    assert list(company.rglob("*.pdf")) == []
    seen = company / ".filingforge_index.json"
    assert not seen.exists() or "news-1" not in seen.read_text(encoding="utf-8")


def test_cover_without_readable_link_uses_bse_notice_only(tmp_path, monkeypatch):
    f = filing(attachment="original-notice.pdf")
    arrange(monkeypatch, [f], {f.news_id: cover(None)})

    result = library.build_library(
        "543210", "KFINTECH", tmp_path, [AR], 2, object(),
        issuer_fetch=lambda *_args: (_ for _ in ()).throw(AssertionError("no link to fetch")),
        link_validator=allow_public,
    )

    pending = result.pending[0]
    assert pending.issuer_url is None
    assert pending.bse_url == (
        "https://www.bseindia.com/xml-data/corpfiling/AttachHis/original-notice.pdf"
    )


def test_unresolved_cover_does_not_block_substantive_sibling(tmp_path, monkeypatch):
    first = filing("cover")
    second = filing("substantive", attachment="full.pdf")
    arrange(monkeypatch, [first, second], {
        "cover": cover(None),
        "substantive": make_pdf(),
    })

    result = library.build_library(
        "543210", "KFINTECH", tmp_path, [AR], 2, object(),
        issuer_fetch=lambda *_args: (_ for _ in ()).throw(AssertionError("no link to fetch")),
        link_validator=allow_public,
    )

    assert result.downloaded == ["substantive"]
    assert [pending.news_id for pending in result.pending] == ["cover"]
    assert result.failed == []
