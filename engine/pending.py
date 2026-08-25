"""Persistent unresolved-document slots for guided local PDF import."""
from __future__ import annotations

from dataclasses import asdict
from datetime import date
import json
import os
import stat
from pathlib import Path
from urllib.parse import urlsplit

from pypdf.errors import PdfReadError

from .converter import pdf_to_markdown
from .errors import FilingForgeError
from .indexer import build_index, build_master_index
from .linked_documents.evidence import (SUPPORTED_FOLDERS, extract_pdf_evidence,
                                        is_linked_cover_letter)
from .linked_documents.models import DocumentContext
from .linked_documents.safety import PDF_MAX_BYTES
from .models import Filing, PendingDocument
from .organiser import filing_destination, load_seen, record_seen, remove_seen

_PENDING_FILE = ".filingforge_pending.json"
_TXN_FILE = ".filingforge_import_txn.json"
_PART = ".part"
_VERSION = 1


class PendingImportError(FilingForgeError):
    def __init__(self, technical: str, user_message: str):
        super().__init__(technical=technical, user_message=user_message)


def _ledger_path(company: Path) -> Path:
    return Path(company) / _PENDING_FILE


def _valid_https_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
        return (
            parsed.scheme.lower() == "https"
            and parsed.hostname is not None
            and parsed.username is None
            and parsed.password is None
            and parsed.port in (None, 443)
        )
    except ValueError:
        return False


def _validated_item(entry: object) -> PendingDocument | None:
    if not isinstance(entry, dict):
        return None
    try:
        item = PendingDocument(**entry)
        date.fromisoformat(item.date[:10])
    except (TypeError, ValueError):
        return None
    required_strings = (
        item.news_id, item.date, item.headline, item.category,
        item.expected_type, item.reason,
    )
    if not all(isinstance(value, str) and value for value in required_strings):
        return None
    if item.folder not in SUPPORTED_FOLDERS:
        return None
    if not _valid_https_url(item.bse_url):
        return None
    if item.issuer_url is not None and not _valid_https_url(item.issuer_url):
        return None
    if item.expected_period is not None and not isinstance(item.expected_period, str):
        return None
    return item


def _read_pending(company: Path) -> list[PendingDocument]:
    path = _ledger_path(company)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("version") != _VERSION or not isinstance(raw.get("items"), list):
            return []
        items = [_validated_item(entry) for entry in raw["items"]]
        if any(item is None for item in items):
            return []
        return [item for item in items if item is not None]
    except (OSError, ValueError, TypeError):
        return []


def list_pending(company: Path) -> list[PendingDocument]:
    company = Path(company)
    recover_pending_import(company)
    items = _read_pending(company)
    seen = load_seen(company)
    current = [item for item in items if item.news_id not in seen]
    if len(current) != len(items):
        _write_pending(company, current)
    return current


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
    if _validated_item(asdict(item)) is None:
        raise ValueError("invalid pending document")
    items = {pending.news_id: pending for pending in list_pending(company)}
    items[item.news_id] = item
    _write_pending(company, sorted(items.values(), key=lambda pending: (pending.date, pending.news_id), reverse=True))


def remove_pending(company: Path, news_id: str) -> None:
    items = list_pending(company)
    if not any(item.news_id == news_id for item in items):
        raise KeyError(news_id)
    _write_pending(company, [item for item in items if item.news_id != news_id])


def remove_pending_if_present(company: Path, news_id: str) -> None:
    items = _read_pending(company)
    if any(item.news_id == news_id for item in items):
        _write_pending(company, [item for item in items if item.news_id != news_id])


def _transaction_path(company: Path) -> Path:
    return Path(company) / _TXN_FILE


def _contained_path(company: Path, relative: object, suffix: str) -> Path | None:
    if not isinstance(relative, str):
        return None
    rel = Path(relative)
    if rel.is_absolute() or rel.suffix.lower() != suffix:
        return None
    root = Path(company).resolve()
    candidate = (root / rel).resolve(strict=False)
    if candidate == root or root not in candidate.parents:
        return None
    return candidate


def _write_transaction(company: Path, news_id: str, pdf_path: Path, md_path: Path) -> None:
    marker = _transaction_path(company)
    partial = marker.with_name(marker.name + _PART)
    partial.write_text(json.dumps({
        "version": _VERSION,
        "news_id": news_id,
        "pdf_rel": pdf_path.relative_to(company).as_posix(),
        "md_rel": md_path.relative_to(company).as_posix(),
    }), encoding="utf-8")
    os.replace(partial, marker)


def recover_pending_import(company: Path) -> None:
    """Roll forward one interrupted assisted import recorded by its durable marker."""
    company = Path(company)
    marker = _transaction_path(company)
    if not marker.exists():
        return
    try:
        raw = json.loads(marker.read_text(encoding="utf-8"))
        if raw.get("version") != _VERSION or not isinstance(raw.get("news_id"), str):
            return
        news_id = raw["news_id"]
        pdf_path = _contained_path(company, raw.get("pdf_rel"), ".pdf")
        md_path = _contained_path(company, raw.get("md_rel"), ".md")
        if pdf_path is None or md_path is None or md_path != pdf_path.with_suffix(".md"):
            return
        pdf_stage = pdf_path.with_name(pdf_path.name + _PART)
        md_stage = md_path.with_name(md_path.name + _PART)
        if not pdf_path.exists() and pdf_stage.exists():
            os.replace(pdf_stage, pdf_path)
        if not md_path.exists() and md_stage.exists():
            os.replace(md_stage, md_path)
        if not (pdf_path.exists() and md_path.exists()):
            for path in (pdf_stage, md_stage, pdf_path, md_path, marker):
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
            remove_seen(company, news_id)
            return
        pending = next((item for item in _read_pending(company) if item.news_id == news_id), None)
        if pending is not None:
            filing = Filing(
                news_id=pending.news_id, date=pending.date, headline=pending.headline,
                attachment=pending.bse_url, folder=pending.folder, category=pending.category,
            )
            record_seen(company, filing)
            remove_pending_if_present(company, news_id)
        build_index(company, company.name)
        build_master_index(company.parent)
        marker.unlink()
    except (OSError, ValueError, TypeError):
        # Keep a valid-looking marker for the next launch; corrupt markers are
        # ignored without touching unrelated library files.
        return


def import_pending_pdf(company: Path, news_id: str, source: Path) -> Path:
    company = Path(company)
    source = Path(source).expanduser()
    pending = next((item for item in list_pending(company) if item.news_id == news_id), None)
    if pending is None:
        raise PendingImportError(
            f"document is no longer pending: {news_id}",
            "That document is no longer pending. Refresh the library and try again.",
        )
    if source.suffix.lower() != ".pdf":
        raise PendingImportError(
            f"not a PDF file: {source}",
            "Choose the full PDF you downloaded from the company website.",
        )
    try:
        with source.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode):
                raise PendingImportError(
                    f"selected path is not a regular file: {source}",
                    "Choose the full PDF you downloaded from the company website.",
                )
            pdf = handle.read(PDF_MAX_BYTES + 1)
    except OSError as exc:
        raise PendingImportError(str(exc), "That PDF could not be read. Choose it again.") from exc
    if len(pdf) > PDF_MAX_BYTES:
        raise PendingImportError(
            f"selected PDF is too large: more than {PDF_MAX_BYTES} bytes",
            "That PDF is too large for FilingForge. Choose a PDF smaller than 100 MB.",
        )
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
    pdf_path = filing_destination(company, filing)
    company_root = company.resolve()
    if company_root not in pdf_path.resolve(strict=False).parents:
        raise PendingImportError(
            "pending destination escapes company directory",
            "That saved request is invalid. Refresh the library and try again.",
        )
    md_path = pdf_path.with_suffix(".md")
    if pdf_path.exists() or md_path.exists() or filing.news_id in load_seen(company):
        raise PendingImportError(
            f"destination already exists for {filing.news_id}",
            "That document already exists in the library. Refresh and use the saved copy.",
        )
    pdf_stage = pdf_path.with_name(pdf_path.name + _PART)
    md_stage = md_path.with_name(md_path.name + _PART)
    marker = _transaction_path(company)
    try:
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_stage.write_bytes(pdf)
        md_stage.write_text(pdf_to_markdown(pdf_stage, filing), encoding="utf-8")
        _write_transaction(company, news_id, pdf_path, md_path)
        os.replace(pdf_stage, pdf_path)
        os.replace(md_stage, md_path)
        record_seen(company, filing)
        remove_pending_if_present(company, news_id)
        build_index(company, company.name)
        build_master_index(company.parent)
        marker.unlink()
        return pdf_path
    except (OSError, KeyError, ValueError) as exc:
        for path in (md_stage, pdf_stage, md_path, pdf_path, marker):
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
