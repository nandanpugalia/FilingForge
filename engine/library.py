"""The orchestrator the glue/UI calls. Resolve is done by the caller (UI picks a Candidate);
here we take a confirmed scrip_code + ticker. Emits progress; partial failures are recorded,
never fatal; INDEX.md is rebuilt at the end so the library is always self-consistent."""
from __future__ import annotations
from pathlib import Path
from .bse_client import BSEClient
from .models import CategorySpec, LibraryResult
from .fetcher import list_filings, download_filing
from .organiser import company_dir, save_filing, already_have, record_seen
from .converter import pdf_to_markdown
from .indexer import build_index, build_master_index
from .progress import ProgressEvent, ProgressCallback, emit
from .errors import FilingForgeError


def _process(company, scrip_code, ticker, specs, years, client, on_progress, everything):
    res = LibraryResult()
    emit(on_progress, ProgressEvent("list", 0, 1, "Finding filings on BSE…"))
    filings = list_filings(scrip_code, specs, years, client, everything=everything)
    total = len(filings)
    for i, f in enumerate(filings, 1):
        label = f.headline or f.attachment
        if already_have(company, f):
            res.skipped.append(f.news_id)
            emit(on_progress, ProgressEvent("download", i, total, f"Already have: {label}"))
            continue
        emit(on_progress, ProgressEvent("download", i, total, f"Downloading {label}…"))
        try:
            pdf = download_filing(f, client)
            pdf_path = save_filing(company, f, pdf)
            pdf_path.with_suffix(".md").write_text(pdf_to_markdown(pdf_path, f), encoding="utf-8")
        except (FilingForgeError, OSError):
            res.failed.append(f.news_id)
            continue
        res.downloaded.append(f.news_id)
        record_seen(company, f)
    emit(on_progress, ProgressEvent("index", total, total, "Updating index…"))
    build_index(company, ticker)
    build_master_index(company.parent)
    return res


def build_library(scrip_code, ticker, root, specs, years, client, on_progress=None,
                  *, everything=False):
    company = company_dir(root, ticker)
    company.mkdir(parents=True, exist_ok=True)
    return _process(company, scrip_code, ticker, specs, years, client, on_progress, everything)


def refresh_library(company, scrip_code, specs, years, client, on_progress=None,
                    *, everything=False):
    company = Path(company)
    return _process(company, scrip_code, company.name, specs, years, client, on_progress, everything)
