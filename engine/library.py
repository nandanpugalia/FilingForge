"""The orchestrator the glue/UI calls. Resolve is done by the caller (UI picks a Candidate);
here we take a confirmed scrip_code + ticker. Emits progress; partial failures are recorded,
never fatal; INDEX.md is rebuilt at the end so the library is always self-consistent."""
from __future__ import annotations
from typing import Callable, Optional
from pathlib import Path
from .bse_client import BSEClient
from .models import CategorySpec, LibraryResult
from .fetcher import list_all_filings, download_filing
from .organiser import (company_dir, save_filing, save_markdown, clean_partials,
                        already_have, record_seen, save_library_config)
from .converter import pdf_to_markdown
from .indexer import build_index, build_master_index
from .report_helper import write_report_helper
from .progress import ProgressEvent, ProgressCallback, emit
from .errors import FilingForgeError

CancelFn = Optional[Callable[[], bool]]

# Headlines that are typically big multi-MB PDFs. A single such download can sit for 20s+ on a
# slow link with the % bar frozen, which users read as "stuck at 10-15%". Flagging it in the
# message makes the wait legible instead of looking like a hang.
_LARGE_DOC_HINTS = ("annual report", "business responsibility", "integrated report", "investor presentation")


def _process(company, scrip_code, ticker, specs, years, client, on_progress, everything,
             should_cancel: CancelFn = None):
    res = LibraryResult()
    clean_partials(company)   # clear any *.part left by a prior interrupted run
    emit(on_progress, ProgressEvent("list", 0, 1, "Finding filings on BSE…"))
    filings = list_all_filings(scrip_code, specs, years, client, everything=everything)
    total = len(filings)
    for i, f in enumerate(filings, 1):
        if should_cancel and should_cancel():   # checked BEFORE each filing → recorded ones are whole
            res.cancelled = True
            break
        label = f.headline or f.attachment
        if already_have(company, f):
            res.skipped.append(f.news_id)
            emit(on_progress, ProgressEvent("download", i, total, f"Already have: {label}"))
            continue
        big = any(h in label.lower() for h in _LARGE_DOC_HINTS)
        hint = " — large file, this can take a moment" if big else ""
        emit(on_progress, ProgressEvent("download", i, total, f"Downloading {label}…{hint}"))
        try:
            pdf = download_filing(f, client)
            pdf_path = save_filing(company, f, pdf)                 # atomic
            save_markdown(pdf_path, pdf_to_markdown(pdf_path, f))   # atomic
        except (FilingForgeError, OSError):
            res.failed.append(f.news_id)
            continue
        res.downloaded.append(f.news_id)
        record_seen(company, f)            # ONLY after both pdf+md succeed → never marks a half-file
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
                  *, everything=False, should_cancel: CancelFn = None):
    company = company_dir(Path(root).expanduser(), ticker)
    company.mkdir(parents=True, exist_ok=True)
    return _process(company, scrip_code, ticker, specs, years, client, on_progress, everything,
                    should_cancel)


def refresh_library(company, scrip_code, specs, years, client, on_progress=None,
                    *, everything=False, should_cancel: CancelFn = None):
    company = Path(company).expanduser()
    return _process(company, scrip_code, company.name, specs, years, client, on_progress, everything,
                    should_cancel)
