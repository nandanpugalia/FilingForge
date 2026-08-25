"""The orchestrator the glue/UI calls. Resolve is done by the caller (UI picks a Candidate);
here we take a confirmed scrip_code + ticker. Emits progress; partial failures are recorded,
never fatal; INDEX.md is rebuilt at the end so the library is always self-consistent."""
from __future__ import annotations
from typing import Callable, Optional
from pathlib import Path
from datetime import date
import re
import httpx
from .bse_client import BSEClient
from .models import CategorySpec, LibraryResult, PendingDocument
from .fetcher import list_all_filings, download_filing, filing_attachment_url
from .organiser import (company_dir, save_filing, save_markdown, clean_partials,
                        already_have, filing_label, record_seen, save_library_config)
from .converter import pdf_to_markdown
from .indexer import build_index, build_master_index, count_documents
from .report_helper import write_report_helper
from .progress import ProgressEvent, ProgressCallback, emit
from .errors import FilingForgeError
from .linked_documents.evidence import (SUPPORTED_FOLDERS, extract_pdf_evidence,
                                        is_linked_cover_letter)
from .linked_documents.models import DocumentContext
from .linked_documents.resolver import resolve_document
from .linked_documents.safety import fetch_public_document, validate_public_https_url
from .pending import list_pending, recover_pending_import, upsert_pending

CancelFn = Optional[Callable[[], bool]]
IssuerFetch = Callable[[str, str], object]
LinkValidator = Callable[[str], str]

# Headlines that are typically big multi-MB PDFs. A single such download can sit for 20s+ on a
# slow link with the % bar frozen, which users read as "stuck at 10-15%". Flagging it in the
# message makes the wait legible instead of looking like a hang.
_LARGE_DOC_HINTS = ("annual report", "business responsibility", "integrated report", "investor presentation")

_EXPECTED_TYPES = {
    "annual-reports": "Annual report",
    "concalls": "Concall transcript",
    "investor-ppts": "Investor presentation",
    "quarterly": "Financial results",
}
_PERIOD_RE = re.compile(
    r"\b(Q[1-4]\s*(?:FY\s*)?\d{2,4}(?:-\d{2})?|FY\s*\d{2,4}(?:-\d{2,4})?|\d{4}-\d{2})\b",
    re.IGNORECASE,
)


def _expected_period(headline: str) -> str | None:
    match = _PERIOD_RE.search(headline)
    if not match:
        return None
    value = " ".join(match.group(1).upper().split())
    if value.startswith("FY") and not value.startswith("FY "):
        value = "FY " + value[2:]
    return value


def _document_context(ticker: str, filing) -> DocumentContext:
    return DocumentContext(
        company=ticker,
        folder=filing.folder,
        filing_date=date.fromisoformat(filing.date[:10]),
        headline=filing.headline,
        source_url=filing_attachment_url(filing),
    )


def _is_cover(context: DocumentContext, pdf: bytes) -> bool:
    if context.folder not in SUPPORTED_FOLDERS:
        return False
    try:
        return is_linked_cover_letter(context, extract_pdf_evidence(pdf))
    except Exception:
        # Preserve the existing converter's honest unreadable/scanned handling. The linked
        # resolver is only allowed to replace a positively identified cover letter.
        return False


def _process(company, scrip_code, ticker, specs, years, client, on_progress, everything,
             should_cancel: CancelFn = None, issuer_fetch=None,
             link_validator: LinkValidator = validate_public_https_url):
    res = LibraryResult()
    recover_pending_import(company)
    clean_partials(company)   # clear any *.part left by a prior interrupted run
    emit(on_progress, ProgressEvent("list", 0, 1, "Finding filings on BSE…"))
    filings = list_all_filings(scrip_code, specs, years, client, everything=everything)
    total = len(filings)
    issuer_client: httpx.Client | None = None

    def default_issuer_fetch(url: str, expected: str):
        nonlocal issuer_client
        if issuer_client is None:
            issuer_client = httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0))
        return fetch_public_document(issuer_client, url, expected=expected)

    linked_fetch = issuer_fetch or default_issuer_fetch
    try:
        for i, f in enumerate(filings, 1):
            if should_cancel and should_cancel():   # checked BEFORE each filing → recorded ones are whole
                res.cancelled = True
                break
            label = filing_label(f)
            if already_have(company, f):
                res.skipped.append(f.news_id)
                emit(on_progress, ProgressEvent("download", i, total, f"Already in your library: {label}"))
                continue
            big = any(h in label.lower() for h in _LARGE_DOC_HINTS)
            hint = " — large file, this can take a moment" if big else ""
            emit(on_progress, ProgressEvent("download", i, total, f"Downloading {label}…{hint}"))
            try:
                pdf = download_filing(f, client)
                context = _document_context(ticker, f)
                if _is_cover(context, pdf):
                    resolution = resolve_document(
                        context, pdf, fetch=linked_fetch, validate=link_validator,
                    )
                    if resolution.status == "unresolved" or resolution.pdf is None:
                        pending = PendingDocument(
                            news_id=f.news_id,
                            date=f.date,
                            headline=f.headline,
                            folder=f.folder,
                            category=f.category,
                            expected_type=_EXPECTED_TYPES[f.folder],
                            expected_period=_expected_period(f.headline),
                            bse_url=filing_attachment_url(f),
                            issuer_url=resolution.action_url,
                            reason=resolution.reason,
                        )
                        upsert_pending(company, pending)
                        res.pending.append(pending)
                        emit(on_progress, ProgressEvent(
                            "download", i, total,
                            f"Full document needs your download: {label}",
                        ))
                        continue
                    pdf = resolution.pdf
                pdf_path = save_filing(company, f, pdf)                 # atomic
                save_markdown(pdf_path, pdf_to_markdown(pdf_path, f))   # atomic
            except (FilingForgeError, OSError):
                res.failed.append(f.news_id)
                continue
            res.downloaded.append(f.news_id)
            record_seen(company, f)            # ONLY after both pdf+md succeed → never marks a half-file
    finally:
        if issuer_client is not None:
            issuer_client.close()
    # Whether finished or cancelled, leave the library consistent: drop any stray *.part,
    # then rebuild the indexes + helper over exactly what is fully on disk.
    clean_partials(company)
    msg = "Stopped — saving what was downloaded…" if res.cancelled else "Updating index…"
    emit(on_progress, ProgressEvent("index", total, total, msg))
    build_index(company, ticker)
    build_master_index(company.parent)
    write_report_helper(company.parent)   # app-managed report template for skills to use
    # remember what categories built this library so a later refresh honours the same choice
    # (not a fresh set of smart defaults that would silently drop filings). everything=True →
    # record [] so the loader's None-vs-[] distinction stays clean.
    save_library_config(company, [s.key for s in specs] if not everything else [], everything)
    # Report the complete persisted state, not just what happened to be inside
    # this build's year/category scope. This keeps refreshes and restarts honest.
    res.pending = list_pending(company)
    res.ready = count_documents(company)
    return res


def preview_library(scrip_code, root, ticker, specs, years, client, *, everything=False) -> dict:
    """List-only (no downloads): how many filings the chosen scope would fetch, broken down by
    category, and how many are already in the library. Stateless — touches no disk. The build
    re-lists at download time, so this is an honest estimate, not a frozen manifest."""
    company = company_dir(Path(root).expanduser(), ticker)
    filings = list_all_filings(scrip_code, specs, years, client, everything=everything)
    existing = company.exists()
    by_cat: dict[str, int] = {}
    new = have = 0
    for f in filings:
        by_cat[f.category] = by_cat.get(f.category, 0) + 1
        if existing and already_have(company, f):
            have += 1
        else:
            new += 1
    by_category = sorted(({"label": k, "count": v} for k, v in by_cat.items()),
                         key=lambda x: (-x["count"], x["label"]))
    return {"total": len(filings), "new": new, "have": have, "by_category": by_category}


def build_library(scrip_code, ticker, root, specs, years, client, on_progress=None,
                  *, everything=False, should_cancel: CancelFn = None,
                  issuer_fetch=None, link_validator: LinkValidator = validate_public_https_url):
    company = company_dir(Path(root).expanduser(), ticker)
    company.mkdir(parents=True, exist_ok=True)
    return _process(company, scrip_code, ticker, specs, years, client, on_progress, everything,
                    should_cancel, issuer_fetch, link_validator)


def refresh_library(company, scrip_code, specs, years, client, on_progress=None,
                    *, everything=False, should_cancel: CancelFn = None,
                    issuer_fetch=None, link_validator: LinkValidator = validate_public_https_url):
    company = Path(company).expanduser()
    return _process(company, scrip_code, company.name, specs, years, client, on_progress, everything,
                    should_cancel, issuer_fetch, link_validator)
