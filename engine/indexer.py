"""Indexes. Per-company INDEX.md (scans real folders on disk) + a master root INDEX.md across all
companies. Always a full rebuild from disk, so neither can drift (idempotent)."""
from __future__ import annotations
from pathlib import Path


def _titleize(folder_name: str) -> str:
    return folder_name.replace("-", " ").title()


def _company_counts(company: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for sub in sorted(p for p in company.iterdir() if p.is_dir()):
        n = len(list(sub.glob("*.pdf")))
        if n:
            counts[sub.name] = n
    return counts


def build_index(company: Path, ticker: str) -> Path:
    lines = [f"# {ticker}", "", "_AI-ready filing library built by FilingForge. "
             "Each document has a clean `.md` sibling for your AI to read._", ""]
    for sub in sorted(p for p in company.iterdir() if p.is_dir()):
        pdfs = sorted(sub.glob("*.pdf"))
        if not pdfs:
            continue
        lines.append(f"## {_titleize(sub.name)}")
        lines.append("")
        for pdf in pdfs:
            stem = pdf.stem
            d = stem[:10]
            title = stem[11:].split("__")[0].replace("_", " ").strip() or pdf.name
            lines.append(f"- **{d}** — {title}  ·  [`{sub.name}/{pdf.name}`]({sub.name}/{pdf.name})")
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
