"""PDF → clean markdown with provenance frontmatter. License-clean (pypdf/BSD, not pymupdf).
Never raises on a bad PDF — returns frontmatter + an explicit 'could not be extracted' marker
so the library stays valid and the UI can show the source even if text extraction failed."""
from __future__ import annotations
from pathlib import Path
from pypdf import PdfReader
from .models import Filing


# Below this many characters across the whole document, the "text" is almost certainly
# scan noise (a watermark, a page number) rather than a real filing — we flag it as scanned
# rather than passing a few junk characters off as the document's content. We do NOT OCR
# (license-clean, no heavy deps by design); we are honest about what couldn't be read.
MIN_TEXT_CHARS = 40

# Some PDFs (fancy-font slide decks) embed subset fonts with no Unicode map, so text
# extraction yields mojibake — non-linguistic noise no extractor can recover (only OCR,
# which we don't do). Real filings (annual reports, concalls) sit ~0.99 ASCII; mojibake
# sits far lower. Below this share of plain printable characters, we treat it as garbled
# and refuse to pass the noise off as the document's text.
GARBLE_RATIO = 0.70


def _printable_ratio(text: str) -> float:
    if not text:
        return 1.0
    ok = sum(1 for c in text if c in " \n\r\t" or 0x20 <= ord(c) <= 0x7E)
    return ok / len(text)


def _strip_garbled_lines(text: str) -> str:
    """Drop individual mojibake lines while keeping the readable ones. A mostly-good slide
    deck can carry a handful of fancy-font lines that extract as noise — remove just those
    so the AI gets the document's real text, not garbage in the middle of it. Short/blank
    lines are kept (too little to judge); longer lines below the printable threshold go."""
    kept = []
    for line in text.split("\n"):
        s = line.strip()
        if len(s) < 8 or _printable_ratio(s) >= 0.60:
            kept.append(line)
    return "\n".join(kept)


def _extract_text(pdf_path: Path) -> str | None:
    try:
        reader = PdfReader(str(pdf_path))
        parts = [(page.extract_text() or "") for page in reader.pages]
        text = "\n\n".join(p.strip() for p in parts if p.strip())
        return _strip_garbled_lines(text) if text else ""   # clean noise; "" if imaged/blank
    except Exception:
        return None         # not a real/parseable PDF


def pdf_to_markdown(pdf_path: Path, filing: Filing) -> str:
    text = _extract_text(Path(pdf_path))
    # status is machine-readable in the frontmatter so the indexer/UI can surface "scanned"
    # without re-parsing the body: ok | thin | empty | failed.
    if text is None:
        status, body = "failed", "_This document could not be extracted to text (it may be a scanned image)._\n"
    elif text == "":
        status, body = "empty", "_No selectable text found (likely a scanned/image PDF). The PDF is saved alongside._\n"
    elif len(text) < MIN_TEXT_CHARS:
        status = "thin"
        body = ("_Very little selectable text was found — this is likely a scanned/image PDF. "
                "The source PDF is saved alongside; what little text was extracted follows._\n\n" + text + "\n")
    elif _printable_ratio(text) < GARBLE_RATIO:
        status = "garbled"
        body = ("_The text in this PDF couldn't be read cleanly — its embedded fonts carry no Unicode "
                "mapping (common in image-heavy slide decks), so extraction produced noise rather than "
                "words. The source PDF is saved alongside; read it directly for this document._\n")
    else:
        status, body = "ok", text + "\n"
    fm = (
        "---\n"
        f"headline: {filing.headline}\n"
        f"date: {filing.date}\n"
        f"category: {filing.category}\n"
        f"source_pdf: {filing.attachment}\n"
        f"news_id: {filing.news_id}\n"
        f"extracted: {status}\n"
        "---\n\n"
    )
    return fm + body
