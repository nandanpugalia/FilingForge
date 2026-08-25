"""Owns the on-disk library layout + incremental dedup. The caller passes a root dir only;
the user never types a path or learns the internal structure (UI-first).

Writes are ATOMIC: every file is written to a sibling ``*.part`` then ``os.replace``-d into
place (atomic on the same filesystem). So an interrupted download — Stop, window-close, crash,
network drop — can only ever leave an inert ``*.part`` (invisible to the ``*.pdf`` index glob),
never a half-written ``.pdf``/``.md`` that the disk-scanning indexer would treat as real."""
from __future__ import annotations
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from .models import Filing

_SEEN_FILE = ".filingforge_index.json"   # hidden per-company dedup ledger (news_ids seen)
_CONFIG_FILE = "library.json"            # per-company record of the categories last used
_PART = ".part"                          # suffix for in-flight writes; cleaned on cancel/restart

_DOCUMENT_LABELS = {
    "annual-reports": "Annual report",
    "concalls": "Concall transcript",
    "investor-ppts": "Investor presentation",
    "quarterly": "Financial results",
}
_MONTH_DATE = (
    r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?[,]?\s+(?P<year>\d{4})"
)
_ENDED_PERIOD_RE = re.compile(
    r"\b(?P<kind>quarter(?:\s+and\s+(?:three|six|nine)\s+months)?|"
    r"(?:three|six|nine)\s+months|half[- ]year|financial year|year)\s+ended\s+" + _MONTH_DATE,
    re.IGNORECASE,
)
_QFY_RE = re.compile(
    r"\b(?P<quarter>Q[1-4])\s*FY\s*(?P<start>\d{2,4})(?:\s*[-/]\s*(?P<end>\d{2,4}))?\b",
    re.IGNORECASE,
)
_FY_RE = re.compile(
    r"\b(?:FY|financial\s+year)\s*(?P<start>\d{4})\s*[-/]\s*(?P<end>\d{2,4})\b",
    re.IGNORECASE,
)
_ANNUAL_YEAR_RE = re.compile(r"\b(?P<start>20\d{2})\s*[-/]\s*(?P<end>\d{2})\b")
_PERIOD_FILENAME_KIND = {
    "quarter and three months": "Quarter_and_3M",
    "quarter and six months": "Quarter_and_6M",
    "quarter and nine months": "Quarter_and_9M",
    "three months": "3M",
    "six months": "6M",
    "nine months": "9M",
    "half year": "Half_year",
    "financial year": "Financial_year",
    "quarter": "Quarter",
    "year": "Year",
}


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + _PART)
    tmp.write_bytes(data)
    os.replace(tmp, path)   # atomic same-fs rename; never leaves a partial final file


def _atomic_write_text(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + _PART)
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def company_dir(root: Path, ticker: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]", "", ticker.upper())
    return Path(root) / safe


def _filing_date_label(value: str) -> str:
    try:
        parsed = datetime.strptime(value[:10], "%Y-%m-%d")
    except ValueError:
        return value[:10]
    return f"{parsed.day} {parsed.strftime('%b %Y')}"


def _period_parts(filing: Filing) -> tuple[str | None, str | None]:
    """Return (human display, filename fragment) only for explicit headline evidence."""
    headline = " ".join(filing.headline.split())
    ended = _ENDED_PERIOD_RE.search(headline)
    if ended:
        parsed = datetime.strptime(
            f"{ended.group('month')} {ended.group('day')} {ended.group('year')}",
            "%B %d %Y",
        )
        kind = ended.group("kind").lower().replace("-", " ")
        display = f"{kind} ended {parsed.day} {parsed.strftime('%b %Y')}"
        filename = f"{_PERIOD_FILENAME_KIND[kind]}_ended_{parsed:%Y-%m-%d}"
        return display, filename

    qfy = _QFY_RE.search(headline)
    if qfy:
        end = qfy.group("end")
        year = qfy.group("start") + (f"-{end}" if end else "")
        fy_join = "FY" if len(qfy.group("start")) == 2 and not end else "FY "
        display = f"{qfy.group('quarter').upper()} {fy_join}{year}"
        return display, display.replace(" ", "_")

    fy = _FY_RE.search(headline)
    if fy:
        display = f"FY {fy.group('start')}-{fy.group('end')}"
        return display, display.replace(" ", "_")

    if filing.folder == "annual-reports":
        annual = _ANNUAL_YEAR_RE.search(headline)
        if annual:
            display = f"FY {annual.group('start')}-{annual.group('end')}"
            return display, display.replace(" ", "_")
    return None, None


def filing_label(filing: Filing) -> str:
    """Concise progress copy for substantive documents; no I/O and no guessed period."""
    document_type = _DOCUMENT_LABELS.get(filing.folder)
    if document_type is None:
        return filing.headline or filing.attachment
    period, _ = _period_parts(filing)
    return f"{document_type} — {period or f'filed {_filing_date_label(filing.date)}'}"


def _safe_name(filing: Filing) -> str:
    # keep hyphens so "2024-25" survives the round-trip into INDEX.md (collapse only
    # truly unsafe runs to "_"); the date prefix is fixed-width YYYY-MM-DD. The
    # "__<news_id>" suffix guarantees uniqueness so same date+headline filings with
    # different NEWSIDs never overwrite each other (silent data loss).
    document_type = _DOCUMENT_LABELS.get(filing.folder)
    _, period_name = _period_parts(filing)
    semantic = "_".join(part for part in (document_type, period_name) if part)
    source = semantic or filing.headline
    head = re.sub(r"[^A-Za-z0-9-]+", "_", source)[:60].strip("_")
    nid = re.sub(r"[^A-Za-z0-9-]+", "", filing.news_id)
    return f"{filing.date}_{head or nid}__{nid}.pdf"


def _year_folder(filing: Filing) -> str:
    """Year subfolder for a filing: 'YYYY' if the date starts with a 4-digit year,
    else 'undated'. Plain numeric string → safe on every OS (incl. Windows)."""
    y = filing.date[:4]
    return y if y.isdigit() and len(y) == 4 else "undated"


def filing_destination(company: Path, filing: Filing) -> Path:
    """Deterministic final PDF path without touching disk."""
    return Path(company) / filing.folder / _year_folder(filing) / _safe_name(filing)


def save_filing(company: Path, filing: Filing, pdf_bytes: bytes) -> Path:
    # NEW layout: <company>/<category-folder>/<YYYY>/<file>.pdf (year-nested for
    # navigability). pathlib keeps this cross-platform; the year is numeric so it is
    # a valid dir name on Windows too. The .md sibling (written by the caller) lands
    # in the same year folder via path.with_suffix(".md").
    path = filing_destination(company, filing)
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_bytes(path, pdf_bytes)
    return path


def save_markdown(pdf_path: Path, md_text: str) -> Path:
    """Atomically write the clean ``.md`` sibling next to a saved PDF and return its path.
    Atomic so a kill between the PDF and MD writes can't leave a half-written Markdown."""
    md = pdf_path.with_suffix(".md")
    _atomic_write_text(md, md_text)
    return md


def clean_partials(company: Path) -> int:
    """Delete any stray ``*.part`` files left by a killed/crashed write. Returns the count
    removed. Run at build start and on cancel so interrupted writes never linger."""
    company = Path(company)
    if not company.exists():
        return 0
    n = 0
    for p in company.rglob("*" + _PART):
        try:
            p.unlink()
            n += 1
        except OSError:
            pass
    return n


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
    _atomic_write_text(company / _SEEN_FILE, json.dumps(sorted(seen)))


def remove_seen(company: Path, news_id: str) -> None:
    """Remove one dedup identity during rollback of a failed assisted import."""
    company = Path(company)
    seen = load_seen(company)
    if news_id not in seen:
        return
    seen.remove(news_id)
    path = company / _SEEN_FILE
    if seen:
        _atomic_write_text(path, json.dumps(sorted(seen)))
    else:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def already_have(company: Path, filing: Filing) -> bool:
    return filing.news_id in load_seen(company)


def save_library_config(company: Path, category_keys: list[str], everything: bool) -> None:
    """Record which categories built this library, so a later refresh can honour the same
    choice instead of silently applying new smart defaults (which would drop filings the
    user previously pulled). Written on every successful build."""
    company = Path(company)
    company.mkdir(parents=True, exist_ok=True)
    (company / _CONFIG_FILE).write_text(
        json.dumps({"version": 1, "categories": sorted(category_keys),
                    "everything": bool(everything)}, indent=2))


def load_library_config(company: Path) -> Optional[dict]:
    """The saved build config, or None for a legacy v0.1.6 library (no config file) — the
    caller treats None as 'pull everything', preserving old behaviour on refresh."""
    f = Path(company) / _CONFIG_FILE
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text())
    except Exception:
        return None
