from pathlib import Path
from engine.converter import pdf_to_markdown
from engine.models import Filing
from engine.tests.conftest import FIXTURES


def _f():
    return Filing(news_id="ar-1", date="2025-07-01", headline="Annual Report 2024-25",
                  attachment="ar1.pdf", folder="annual-reports", category="Annual Reports")


def test_markdown_has_frontmatter_with_provenance():
    md = pdf_to_markdown(FIXTURES / "minimal.pdf", _f())
    assert md.startswith("---\n")
    assert "headline: Annual Report 2024-25" in md
    assert "date: 2025-07-01" in md
    assert "source_pdf: ar1.pdf" in md
    assert "category: Annual Reports" in md


def test_corrupt_pdf_yields_frontmatter_and_empty_body_not_crash(tmp_path):
    bad = tmp_path / "bad.pdf"; bad.write_bytes(b"not a pdf at all")
    md = pdf_to_markdown(bad, _f())
    assert md.startswith("---\n")            # never raises; body just empty/marked
    assert "could not be extracted" in md.lower()
