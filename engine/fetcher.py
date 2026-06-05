"""List + download BSE filings (endpoints confirmed in spike). Pure over the BSEClient seam."""
from __future__ import annotations
from datetime import date, timedelta
from .bse_client import BSEClient
from .errors import DownloadError
from .models import Filing, CategorySpec, slug

ANN_URL = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"
_PDF_BASES = [   # SPIKE FINDING: AttachHis serves real %PDF; AttachLive is stale (HTML). Try both.
    "https://www.bseindia.com/xml-data/corpfiling/AttachHis/",
    "https://www.bseindia.com/xml-data/corpfiling/AttachLive/",
]
_MAX_PAGES = 50


def _classify(row: dict, specs: list[CategorySpec], everything: bool):
    """Return (folder, category_label) if this row should be kept, else None."""
    cat = (row.get("CATEGORYNAME") or "").strip()
    sub = (row.get("SUBCATNAME") or "").strip()
    if everything:
        return (slug(cat), cat or "Other")
    for spec in specs:
        if spec.matches(cat, sub):
            return (spec.folder, spec.label)
    return None


def list_filings(scrip_code: str, specs: list[CategorySpec], years: int, client: BSEClient,
                 *, everything: bool = False) -> list[Filing]:
    end = date.today()
    start = end - timedelta(days=365 * years)
    base = {"strCat": "-1", "subcategory": "-1", "strSearch": "P", "strType": "C",
            "strScrip": str(scrip_code),
            "strPrevDate": start.strftime("%Y%m%d"), "strToDate": end.strftime("%Y%m%d")}
    out: list[Filing] = []
    for pageno in range(1, _MAX_PAGES + 1):
        rows = client.get_json(ANN_URL, {**base, "pageno": str(pageno)}).get("Table") or []
        if not rows:
            break
        for row in rows:
            hit = _classify(row, specs, everything)
            if hit is None:
                continue
            att = (row.get("ATTACHMENTNAME") or "").strip()
            if not att:
                continue
            folder, category = hit
            out.append(Filing(
                news_id=str(row.get("NEWSID") or att),
                date=(row.get("DissemDT") or "")[:10],
                headline=(row.get("HEADLINE") or row.get("NEWSSUB") or "").strip(),
                attachment=att, folder=folder, category=category,
            ))
        if len(rows) < 10:
            break
    return out


def download_filing(filing: Filing, client: BSEClient) -> bytes:
    """Return validated PDF bytes. Tries AttachHis then AttachLive; verifies the %PDF magic.
    Raises DownloadError (friendly) if no base yields a real PDF."""
    for base in _PDF_BASES:
        content = client.get_bytes(base + filing.attachment)
        if content[:5] == b"%PDF-":
            return content
    raise DownloadError(filing.headline or filing.attachment)
