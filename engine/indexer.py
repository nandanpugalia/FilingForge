"""Indexes. Per-company INDEX.md (scans real folders on disk) + a master root INDEX.md across all
companies. Always a full rebuild from disk, so neither can drift (idempotent)."""
from __future__ import annotations
from pathlib import Path


def _titleize(folder_name: str) -> str:
    return folder_name.replace("-", " ").title()


def _year_of(pdf: Path) -> str:
    """Year group for a pdf, derived from the filename's leading YYYY-MM-DD (NOT the
    folder depth). Works identically for flat and year-nested libraries. Falls back to
    'Undated' when the stem does not start with a 4-digit year."""
    y = pdf.stem[:4]
    return y if y.isdigit() and len(y) == 4 else "Undated"


def _company_counts(company: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for sub in sorted(p for p in company.iterdir() if p.is_dir()):
        # rglob → counts pdfs whether flat (category/*.pdf) or year-nested
        # (category/YYYY/*.pdf). Counts stay keyed by the category folder name.
        n = len(list(sub.rglob("*.pdf")))
        if n:
            counts[sub.name] = n
    return counts


def build_index(company: Path, ticker: str) -> Path:
    lines = [f"# {ticker}", "", "_AI-ready filing library built by FilingForge. "
             "Each document has a clean `.md` sibling for your AI to read._", ""]
    for sub in sorted(p for p in company.iterdir() if p.is_dir()):
        # rglob catches both flat and year-nested layouts (migration-free)
        pdfs = list(sub.rglob("*.pdf"))
        if not pdfs:
            continue
        lines.append(f"## {_titleize(sub.name)}")
        lines.append("")
        # group by YEAR derived from the FILENAME (so flat libraries group too)
        by_year: dict[str, list[Path]] = {}
        for pdf in pdfs:
            by_year.setdefault(_year_of(pdf), []).append(pdf)
        # years descending; "Undated" (non-numeric) sorts last
        for year in sorted(by_year, key=lambda y: (y.isdigit(), y), reverse=True):
            lines.append(f"### {year}")
            lines.append("")
            # within a year, newest date first (filename starts with YYYY-MM-DD)
            for pdf in sorted(by_year[year], key=lambda p: p.name, reverse=True):
                stem = pdf.stem
                d = stem[:10]
                title = stem[11:].split("__")[0].replace("_", " ").strip() or pdf.name
                # link path RELATIVE TO COMPANY DIR (correct flat or nested);
                # as_posix() → forward slashes so markdown links work on Windows too
                rel = pdf.relative_to(company).as_posix()
                lines.append(f"- **{d}** — {title}  ·  [`{rel}`]({rel})")
            lines.append("")
    path = company / "INDEX.md"
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def _is_company_dir(p: Path) -> bool:
    # A company dir is any subdir that has been indexed (INDEX.md) OR already holds
    # filings (a category subfolder with PDFs). Plain root files like a stray
    # INDEX.md or notes.txt are not dirs, so they are ignored.
    if not p.is_dir():
        return False
    return (p / "INDEX.md").exists() or bool(_company_counts(p))


def build_master_index(root: Path) -> Path:
    root = Path(root)
    lines = ["# FilingForge Library", "",
             "_Your local library of Indian company filings. Point your AI at this folder — it can "
             "read each company's `INDEX.md` to navigate every document._", ""]
    companies = sorted(p for p in root.iterdir() if _is_company_dir(p))
    if not companies:
        lines.append("_No companies yet._")
    for c in companies:
        counts = _company_counts(c)
        total = sum(counts.values())
        breakdown = ", ".join(f"{n} {_titleize(k).lower()}" for k, n in counts.items())
        lines.append(f"- **[{c.name}]({c.name}/INDEX.md)** — {total} documents"
                     + (f" ({breakdown})" if breakdown else ""))
    path = root / "INDEX.md"
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def _find_report(company: Path, root: Path) -> str | None:
    """The company's generated research report, if any. Scans only
    company/research_report/*.html (non-recursive — no deep crawl). Prefers
    business_model.html, else the first html alphabetically. Returns the path
    relative to the library root as posix, or None."""
    rr = company / "research_report"
    if not rr.is_dir():
        return None
    htmls = sorted(rr.glob("*.html"), key=lambda p: p.name)
    if not htmls:
        return None
    preferred = rr / "business_model.html"
    chosen = preferred if preferred in htmls else htmls[0]
    return chosen.relative_to(root).as_posix()


def read_library(root: Path) -> list[dict]:
    """Machine-readable library listing for the app's Library view (one dict per company)."""
    root = Path(root).expanduser()
    if not root.exists():
        return []
    out: list[dict] = []
    for c in sorted(p for p in root.iterdir() if _is_company_dir(p)):
        counts = _company_counts(c)
        report_rel = _find_report(c, root)
        out.append({"ticker": c.name, "counts": counts, "total": sum(counts.values()),
                    "hasReport": report_rel is not None, "reportRel": report_rel})
    return out
