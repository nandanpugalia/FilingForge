"""Owns the on-disk library layout + incremental dedup. The caller passes a root dir only;
the user never types a path or learns the internal structure (UI-first)."""
from __future__ import annotations
import json
import re
from pathlib import Path
from .models import Filing

_SEEN_FILE = ".filingforge_index.json"   # hidden per-company dedup ledger (news_ids seen)


def company_dir(root: Path, ticker: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]", "", ticker.upper())
    return Path(root) / safe


def _safe_name(filing: Filing) -> str:
    # keep hyphens so "2024-25" survives the round-trip into INDEX.md (collapse only
    # truly unsafe runs to "_"); the date prefix is fixed-width YYYY-MM-DD. The
    # "__<news_id>" suffix guarantees uniqueness so same date+headline filings with
    # different NEWSIDs never overwrite each other (silent data loss).
    head = re.sub(r"[^A-Za-z0-9-]+", "_", filing.headline)[:60].strip("_")
    nid = re.sub(r"[^A-Za-z0-9-]+", "", filing.news_id)
    return f"{filing.date}_{head or nid}__{nid}.pdf"


def _year_folder(filing: Filing) -> str:
    """Year subfolder for a filing: 'YYYY' if the date starts with a 4-digit year,
    else 'undated'. Plain numeric string → safe on every OS (incl. Windows)."""
    y = filing.date[:4]
    return y if y.isdigit() and len(y) == 4 else "undated"


def save_filing(company: Path, filing: Filing, pdf_bytes: bytes) -> Path:
    # NEW layout: <company>/<category-folder>/<YYYY>/<file>.pdf (year-nested for
    # navigability). pathlib keeps this cross-platform; the year is numeric so it is
    # a valid dir name on Windows too. The .md sibling (written by the caller) lands
    # in the same year folder via path.with_suffix(".md").
    folder = company / filing.folder / _year_folder(filing)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / _safe_name(filing)
    path.write_bytes(pdf_bytes)
    return path


def load_seen(company: Path) -> set[str]:
    f = company / _SEEN_FILE
    if not f.exists():
        return set()
    try:
        return set(json.loads(f.read_text()))
    except Exception:
        return set()


def record_seen(company: Path, filing: Filing) -> None:
    company.mkdir(parents=True, exist_ok=True)
    seen = load_seen(company)
    seen.add(filing.news_id)
    (company / _SEEN_FILE).write_text(json.dumps(sorted(seen)))


def already_have(company: Path, filing: Filing) -> bool:
    return filing.news_id in load_seen(company)
