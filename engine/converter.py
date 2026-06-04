"""PDF → clean markdown with provenance frontmatter. License-clean (pypdf/BSD, not pymupdf).
Never raises on a bad PDF — returns frontmatter + an explicit 'could not be extracted' marker
so the library stays valid and the UI can show the source even if text extraction failed."""
from __future__ import annotations
from pathlib import Path
from pypdf import PdfReader
from .models import Filing


def _extract_text(pdf_path: Path) -> str | None:
    try:
        reader = PdfReader(str(pdf_path))
        parts = [(page.extract_text() or "") for page in reader.pages]
        text = "\n\n".join(p.strip() for p in parts if p.strip())
        return text or ""   # valid PDF, possibly imaged/blank → empty string
    except Exception:
        return None         # not a real/parseable PDF


def pdf_to_markdown(pdf_path: Path, filing: Filing) -> str:
    text = _extract_text(Path(pdf_path))
    fm = (
        "---\n"
        f"headline: {filing.headline}\n"
        f"date: {filing.date}\n"
        f"type: {filing.kind.name.lower()}\n"
        f"source_pdf: {filing.attachment}\n"
        f"news_id: {filing.news_id}\n"
        "---\n\n"
    )
    if text is None:
        body = "_This document could not be extracted to text (it may be a scanned image)._\n"
    elif text == "":
        body = "_No selectable text found (likely a scanned/image PDF). The PDF is saved alongside._\n"
    else:
        body = text + "\n"
    return fm + body
