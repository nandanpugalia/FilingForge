"""Persistent unresolved-document slots for guided local PDF import."""
from __future__ import annotations

from dataclasses import asdict
from datetime import date
import json
import os
from pathlib import Path

from pypdf.errors import PdfReadError

from .converter import pdf_to_markdown
from .errors import FilingForgeError
from .indexer import build_index, build_master_index
from .linked_documents.evidence import extract_pdf_evidence, is_linked_cover_letter
from .linked_documents.models import DocumentContext
from .linked_documents.safety import PDF_MAX_BYTES
from .models import Filing, PendingDocument
from .organiser import record_seen, remove_seen, save_filing, save_markdown

_PENDING_FILE = ".filingforge_pending.json"
_PART = ".part"
_VERSION = 1


class PendingImportError(FilingForgeError):
    def __init__(self, technical: str, user_message: str):
        super().__init__(technical=technical, user_message=user_message)


def _ledger_path(company: Path) -> Path:
    return Path(company) / _PENDING_FILE


def list_pending(company: Path) -> list[PendingDocument]:
    path = _ledger_path(company)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("version") != _VERSION or not isinstance(raw.get("items"), list):
            return []
        return [PendingDocument(**entry) for entry in raw["items"]]
    except (OSError, ValueError, TypeError):
        return []


def _write_pending(company: Path, items: list[PendingDocument]) -> None:
    company = Path(company)
    company.mkdir(parents=True, exist_ok=True)
    path = _ledger_path(company)
    if not items:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        return
    partial = path.with_name(path.name + _PART)
    partial.write_text(
        json.dumps({"version": _VERSION, "items": [asdict(item) for item in items]}, indent=2),
        encoding="utf-8",
    )
    os.replace(partial, path)


def upsert_pending(company: Path, item: PendingDocument) -> None:
    items = {pending.news_id: pending for pending in list_pending(company)}
    items[item.news_id] = item
    _write_pending(company, sorted(items.values(), key=lambda pending: (pending.date, pending.news_id), reverse=True))


def remove_pending(company: Path, news_id: str) -> None:
    items = list_pending(company)
    if not any(item.news_id == news_id for item in items):
        raise KeyError(news_id)
    _write_pending(company, [item for item in items if item.news_id != news_id])


def import_pending_pdf(company: Path, news_id: str, source: Path) -> Path:
    company = Path(company)
    source = Path(source).expanduser()
    pending = next((item for item in list_pending(company) if item.news_id == news_id), None)
    if pending is None:
        raise PendingImportError(
            f"document is no longer pending: {news_id}",
            "That document is no longer pending. Refresh the library and try again.",
        )
    if not source.is_file() or source.suffix.lower() != ".pdf":
        raise PendingImportError(
            f"not a PDF file: {source}",
            "Choose the full PDF you downloaded from the company website.",
        )
    try:
        size = source.stat().st_size
    except OSError as exc:
        raise PendingImportError(str(exc), "That PDF could not be read. Choose it again.") from exc
    if size > PDF_MAX_BYTES:
        raise PendingImportError(
            f"selected PDF is too large: {size} bytes",
            "That PDF is too large for FilingForge. Choose a PDF smaller than 100 MB.",
        )

    try:
        pdf = source.read_bytes()
    except OSError as exc:
        raise PendingImportError(str(exc), "That PDF could not be read. Choose it again.") from exc
    if not pdf.startswith(b"%PDF-"):
        raise PendingImportError(
            f"selected file lacks PDF magic: {source}",
            "That file is not a readable PDF. Choose the full document PDF.",
        )

    try:
        evidence = extract_pdf_evidence(pdf)
    except (PdfReadError, ValueError, OSError) as exc:
        raise PendingImportError(
            f"selected PDF is unreadable: {type(exc).__name__}",
            "That PDF appears damaged or incomplete. Download it again and retry.",
        ) from exc

    context = DocumentContext(
        company=company.name,
        folder=pending.folder,
        filing_date=date.fromisoformat(pending.date[:10]),
        headline=pending.headline,
        source_url=pending.bse_url,
    )
    if is_linked_cover_letter(context, evidence):
        raise PendingImportError(
            "selected PDF is another linked cover letter",
            "That is another cover letter, not the full document. Download the document itself and retry.",
        )

    filing = Filing(
        news_id=pending.news_id,
        date=pending.date,
        headline=pending.headline,
        attachment=pending.bse_url,
        folder=pending.folder,
        category=pending.category,
    )
    pdf_path: Path | None = None
    md_path: Path | None = None
    try:
        pdf_path = save_filing(company, filing, pdf)
        md_path = save_markdown(pdf_path, pdf_to_markdown(pdf_path, filing))
        build_index(company, company.name)
        build_master_index(company.parent)
        record_seen(company, filing)
        remove_pending(company, news_id)
        return pdf_path
    except (OSError, KeyError) as exc:
        for path in (md_path, pdf_path):
            if path is not None:
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
        remove_seen(company, news_id)
        upsert_pending(company, pending)
        try:
            build_index(company, company.name)
            build_master_index(company.parent)
        except OSError:
            pass
        raise PendingImportError(
            f"assisted import failed: {type(exc).__name__}: {exc}",
            "FilingForge couldn't add that PDF. Your download is untouched; please try again.",
        ) from exc
