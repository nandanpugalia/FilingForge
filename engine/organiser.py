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
    head = re.sub(r"[^A-Za-z0-9]+", "_", filing.headline)[:60].strip("_")
    return f"{filing.date}_{head or filing.news_id}.pdf"


def save_filing(company: Path, filing: Filing, pdf_bytes: bytes) -> Path:
    folder = company / filing.kind.folder
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
