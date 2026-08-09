"""MCP tool layer over a FilingForge library — pure functions, no SDK.

`server.py` is a thin adapter that registers these as MCP tools. Keeping the
behaviour here means it is testable on its own and the SDK stays an optional
dependency.

The library on disk, as the engine writes it:

    <root>/<TICKER>/<category-folder>/<YYYY>/<YYYY-MM-DD>_<Headline>__<id>.pdf
                                            + the .md sibling
    <root>/<TICKER>/INDEX.md
    <root>/INDEX.md

Every path that arrives from a caller is resolved and checked to be inside the
library root before anything is read. An MCP tool is driven by a model, so a
path argument is untrusted input, not a convenience.
"""
from __future__ import annotations

from pathlib import Path

from engine.library import build_library as _build_library
from engine.library import refresh_library as _refresh_library
from engine.models import CURATED_BY_KEY, default_category_keys
from engine.organiser import load_library_config
from engine.resolver import resolve as _resolve

INDEX_NAME = "INDEX.md"
_HIDDEN_PREFIXES = (".", "_")


def _root(root) -> Path:
    return Path(root).expanduser()


def _company_dirs(root: Path):
    if not root.is_dir():
        return []
    return sorted(
        (d for d in root.iterdir() if d.is_dir() and not d.name.startswith(_HIDDEN_PREFIXES)),
        key=lambda d: d.name,
    )


def list_companies(root) -> list[dict]:
    """Every company in the library, with how much is in it."""
    out = []
    for company in _company_dirs(_root(root)):
        categories = sorted(
            d.name for d in company.iterdir()
            if d.is_dir() and not d.name.startswith(_HIDDEN_PREFIXES)
            and any(d.rglob("*.pdf"))
        )
        out.append({
            "ticker": company.name,
            "filings": len(list(company.rglob("*.pdf"))),
            "categories": categories,
        })
    return out


def get_index(root, ticker: str | None = None) -> str:
    """A company's INDEX.md, or the master index when no company is named.

    Returns "" when the index has not been built yet — a library that exists but
    has not been indexed is a normal state, not an error.
    """
    base = _root(root)
    index = (base / ticker / INDEX_NAME) if ticker else (base / INDEX_NAME)
    try:
        _guard(base, index)
    except ValueError:
        raise
    return index.read_text(encoding="utf-8", errors="replace") if index.is_file() else ""


def search_filings(root, query: str, *, ticker: str | None = None,
                   category: str | None = None, year: str | None = None,
                   limit: int = 50) -> list[dict]:
    """Filings whose filename contains `query`, newest first.

    Matches on the filename because that is where the engine puts the date and
    the headline. An empty query returns everything in scope, so the filters
    alone are a valid way to browse.
    """
    base = _root(root)
    needle = (query or "").strip().lower()

    hits: list[dict] = []
    for company in _company_dirs(base):
        if ticker and company.name != ticker:
            continue
        for pdf in company.rglob("*.pdf"):
            rel = pdf.relative_to(base)
            parts = rel.parts
            if len(parts) < 3:
                continue
            cat, yr = parts[1], parts[2]
            if category and cat != category:
                continue
            if year and yr != year:
                continue
            if needle and needle not in pdf.stem.lower().replace("_", " "):
                continue
            hits.append({
                "ticker": company.name,
                "category": cat,
                "year": yr,
                "date": pdf.stem[:10],
                "title": pdf.stem,
                "path": rel.as_posix(),
                "has_markdown": pdf.with_suffix(".md").is_file(),
            })

    hits.sort(key=lambda h: (h["date"], h["title"]), reverse=True)
    return hits[:limit]


def read_filing(root, path: str) -> str:
    """The clean Markdown for a filing.

    A `.pdf` path is served as its `.md` sibling — the whole point of the
    library is that the model reads clean Markdown, never the binary.
    """
    base = _root(root)
    target = (base / path) if not Path(path).is_absolute() else Path(path)
    if target.suffix.lower() == ".pdf":
        target = target.with_suffix(".md")
    target = _guard(base, target)
    if not target.is_file():
        raise FileNotFoundError(f"no filing at {path}")
    return target.read_text(encoding="utf-8", errors="replace")


def _guard(base: Path, target: Path) -> Path:
    """Resolve `target` and refuse anything outside the library root.

    Called before every read. `..`, symlinks and absolute paths all collapse
    under resolve(), so one check covers them.
    """
    base_r = base.resolve()
    target_r = target.resolve()
    if base_r != target_r and base_r not in target_r.parents:
        raise ValueError(f"path escapes the library: {target}")
    return target_r


def _specs(category_keys):
    """CategorySpecs for the requested keys, or the high-signal defaults.

    An unknown key is an error rather than a silent drop: a model that mistypes
    a category should be told, not handed a library quietly missing a slice.
    """
    keys = list(category_keys) if category_keys else default_category_keys()
    unknown = [k for k in keys if k not in CURATED_BY_KEY]
    if unknown:
        raise ValueError(
            f"unknown categories {unknown}; choose from {sorted(CURATED_BY_KEY)}"
        )
    return [CURATED_BY_KEY[k] for k in keys]


def _summary(status, ticker, result):
    return {
        "status": status,
        "ticker": ticker,
        "downloaded": len(result.downloaded),
        "skipped": len(result.skipped),
        "failed": len(result.failed),
        "cancelled": result.cancelled,
    }


def pull_company(name, root, *, years, client, categories=None, ticker=None):
    """Build a library for `name`, resolving it against BSE first.

    Never guesses. If the name matches more than one company the choices come
    back untouched and nothing is downloaded — picking for the caller is how a
    model ends up with a library for the wrong Escorts.

    Pass a numeric scrip code with an explicit `ticker` to skip resolution.
    """
    specs = _specs(categories)
    name = str(name).strip()

    if name.isdigit():
        if not ticker:
            raise ValueError("a scrip code needs an explicit ticker for the folder name")
        scrip_code, folder = name, ticker
    else:
        matches = _resolve(name, client)
        if not matches:
            return {"status": "not_found", "query": name, "candidates": []}
        if len(matches) > 1:
            return {
                "status": "ambiguous",
                "query": name,
                "candidates": [
                    {"scrip_code": c.scrip_code, "company": c.company,
                     "symbol": c.symbol, "is_primary": c.is_primary}
                    for c in matches
                ],
            }
        only = matches[0]
        scrip_code = only.scrip_code
        folder = ticker or only.symbol or only.scrip_code

    result = _build_library(scrip_code, folder, str(_root(root)), specs, years, client)
    return _summary("built", folder, result)


def refresh_company(root, ticker, *, client, years=None):
    """Re-pull a company already in the library, honouring the categories it was
    built with so a refresh never silently narrows an existing library."""
    company = _root(root) / ticker
    if not company.is_dir():
        return {"status": "not_in_library", "ticker": ticker}

    config = load_library_config(company) or {}
    specs = _specs(config.get("categories"))
    matches = _resolve(ticker, client)
    if not matches:
        return {"status": "not_found", "ticker": ticker, "candidates": []}

    result = _refresh_library(company, matches[0].scrip_code, specs,
                              years or 25, client,
                              everything=bool(config.get("everything")))
    return _summary("refreshed", ticker, result)
