"""The orchestrator the glue/UI calls. Resolve is done by the caller (UI picks a Candidate);
here we take a confirmed scrip_code + ticker. Emits progress; partial failures are recorded,
never fatal; INDEX.md is rebuilt at the end so the library is always self-consistent."""
from __future__ import annotations
from pathlib import Path
from .bse_client import BSEClient
from .models import FilingType, LibraryResult
from .fetcher import list_filings, download_filing
from .organiser import company_dir, save_filing, already_have, record_seen
from .converter import pdf_to_markdown
from .indexer import build_index
from .progress import ProgressEvent, ProgressCallback, emit
from .errors import FilingForgeError


def _process(company: Path, scrip_code: str, ticker: str, kinds: list[FilingType],
             years: int, client: BSEClient, on_progress: ProgressCallback) -> LibraryResult:
    res = LibraryResult()
    emit(on_progress, ProgressEvent("list", 0, 1, "Finding filings on BSE…"))
    filings = list_filings(scrip_code, kinds, years, client)
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
            md_text = pdf_to_markdown(pdf_path, f)
            pdf_path.with_suffix(".md").write_text(md_text, encoding="utf-8")
        except FilingForgeError:
            res.failed.append(f.news_id)
            continue
        res.downloaded.append(f.news_id)
        record_seen(company, f)
    emit(on_progress, ProgressEvent("index", total, total, "Updating index…"))
    build_index(company, ticker)
    return res


def build_library(scrip_code: str, ticker: str, root: Path, kinds: list[FilingType],
                  years: int, client: BSEClient, on_progress: ProgressCallback = None) -> LibraryResult:
    company = company_dir(root, ticker)
    company.mkdir(parents=True, exist_ok=True)
    return _process(company, scrip_code, ticker, kinds, years, client, on_progress)


def refresh_library(company: Path, scrip_code: str, kinds: list[FilingType], years: int,
                    client: BSEClient, on_progress: ProgressCallback = None) -> LibraryResult:
    company = Path(company)
    ticker = company.name
    return _process(company, scrip_code, ticker, kinds, years, client, on_progress)
