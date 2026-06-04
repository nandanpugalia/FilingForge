"""Build INDEX.md from actual folder contents — the table-of-contents the AI reads first.
Always a full rebuild, so it can never drift from what's on disk (spec idempotent)."""
from __future__ import annotations
from pathlib import Path
from .models import FilingType

_SECTION_TITLE = {
    FilingType.ANNUAL_REPORT: "Annual Reports",
    FilingType.RESULTS: "Quarterly",
    FilingType.INVESTOR_PPT: "Investor Presentations",
    FilingType.CONCALL: "Concalls",
}


def build_index(company: Path, ticker: str) -> Path:
    lines = [f"# {ticker}", "", "_AI-ready filing library built by FilingForge. "
             "Each document has a clean `.md` sibling for your AI to read._", ""]
    for kind in FilingType:
        folder = company / kind.folder
        if not folder.exists():
            continue
        pdfs = sorted(folder.glob("*.pdf"))
        if not pdfs:
            continue
        lines.append(f"## {_SECTION_TITLE[kind]}")
        lines.append("")
        for pdf in pdfs:
            # filename is "<date>_<headline>.pdf" → surface date + a readable title
            stem = pdf.stem
            date = stem[:10]
            title = stem[11:].replace("_", " ").strip() or pdf.name
            lines.append(f"- **{date}** — {title}  ·  [`{kind.folder}/{pdf.name}`]({kind.folder}/{pdf.name})")
        lines.append("")
    path = company / "INDEX.md"
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
