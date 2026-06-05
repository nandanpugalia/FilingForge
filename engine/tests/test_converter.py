from pathlib import Path
import engine.converter as conv
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


# --- honesty about scanned / low-text PDFs (we do NOT OCR; we flag) ---

def test_good_text_is_marked_extracted_ok(monkeypatch):
    monkeypatch.setattr(conv, "_extract_text", lambda p: "Tanla Platforms reported revenue growth " * 5)
    md = pdf_to_markdown(Path("x.pdf"), _f())
    assert "extracted: ok" in md
    assert "Tanla Platforms reported" in md


def test_thin_extraction_is_flagged_as_scanned_not_passed_as_content(monkeypatch):
    # a scanned page can leak a few junk chars; that must not masquerade as a full filing
    monkeypatch.setattr(conv, "_extract_text", lambda p: "Page 1")
    md = pdf_to_markdown(Path("x.pdf"), _f())
    assert "extracted: thin" in md
    assert "scanned" in md.lower()           # honest marker
    assert "Page 1" in md                    # but the little we found is still preserved


def test_empty_extraction_status_and_marker(monkeypatch):
    monkeypatch.setattr(conv, "_extract_text", lambda p: "")
    md = pdf_to_markdown(Path("x.pdf"), _f())
    assert "extracted: empty" in md
    assert "scanned" in md.lower()


def test_failed_extraction_status_and_marker(monkeypatch):
    monkeypatch.setattr(conv, "_extract_text", lambda p: None)
    md = pdf_to_markdown(Path("x.pdf"), _f())
    assert "extracted: failed" in md
    assert "could not be extracted" in md.lower()


def test_garbled_extraction_is_flagged_not_passed_as_content(monkeypatch):
    # pypdf emits mojibake for fancy-font slide decks (embedded fonts, no Unicode map).
    # That non-linguistic noise must NOT reach the AI as if it were the filing's text.
    monkeypatch.setattr(conv, "_extract_text",
                        lambda p: "ÖËõÙ©ËéÝ Ë£ Ý¬¤ÅƴÙ¬ôÅ Ƥ ¾¬£Ýäû¾ ä©Ý ©ô Ý©ÖÅÙÙä¬ôÝ \x02\x01 ÖÙÝÅä" * 4)
    md = pdf_to_markdown(Path("x.pdf"), _f())
    assert "extracted: garbled" in md
    assert "couldn't be read" in md.lower()


def test_clean_english_text_is_not_garbled(monkeypatch):
    # a normal text PDF (concalls, annual reports) sits ~0.99 ASCII — must stay "ok"
    monkeypatch.setattr(conv, "_extract_text",
                        lambda p: "Titan Company reported strong revenue growth across its jewellery and watches segments. " * 4)
    md = pdf_to_markdown(Path("x.pdf"), _f())
    assert "extracted: ok" in md


def test_strip_garbled_lines_drops_mojibake_keeps_clean_text():
    # a mostly-good slide deck (clean text + a few fancy-font mojibake lines): keep the signal,
    # drop the noise, so the AI isn't handed garbage in the middle of a real document.
    raw = ("Many People see us as a Jewellery Company\n"
           "ÖËõÙ©ËéÝ Ë£ Ý¬¤ÅƴÙ¬ôÅ Ƥ ¾¬£Ýäû¾ ä©Ý ©ô Ý©ÖÅ\n"
           "Watches Division grew in the premium segment\n"
           "\x02\x01Å¤¤¬Å¤ ä© éÝäËÄÙ Åô¬¬Å¤ õ¬ä© ä©Äƨ\n"
           "FY26 total income crossed seventy six thousand crore")
    out = conv._strip_garbled_lines(raw)
    assert "Many People see us as a Jewellery Company" in out
    assert "Watches Division grew" in out
    assert "FY26 total income crossed" in out
    assert "ÖËõÙ" not in out and "Å¤¤¬Å¤" not in out   # the mojibake lines are gone
