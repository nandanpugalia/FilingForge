"""List + download BSE filings (endpoints confirmed in spike). Pure over the BSEClient seam."""
from __future__ import annotations
from datetime import date, timedelta
from .bse_client import BSEClient
from .errors import DownloadError, FilingForgeError
from .models import Filing, CategorySpec, slug

ANN_URL = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"
_PDF_BASES = [   # SPIKE FINDING: AttachHis serves real %PDF; AttachLive is stale (HTML). Try both.
    "https://www.bseindia.com/xml-data/corpfiling/AttachHis/",
    "https://www.bseindia.com/xml-data/corpfiling/AttachLive/",
]
_MAX_PAGES = 50

# BSE's SECOND filing source. Annual reports only reach the announcements feed
# from 2015, when LODR Reg. 34(1) started requiring them; this archive carries
# them from 1997, for delisted companies as well as live ones. It is what takes
# a library's coverage back two decades.
AR_URL = "https://api.bseindia.com/BseIndiaAPI/api/AnnualReport_New/w"


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


def list_annual_reports(scrip_code: str, client: BSEClient, *, years: int | None = None) -> list[Filing]:
    """Every annual report BSE has archived for a scrip, newest financial year first.

    Unlike the announcements feed this hands back a FULL pdf URL, in one of three
    shapes depending on the era the report was filed in — so the URL is carried
    through as the attachment and `download_filing` fetches it directly.

    `years` caps how far back to read; omit it to take the whole archive.
    """
    rows = client.get_json(AR_URL, {"scripcode": str(scrip_code)}).get("Table") or []
    latest = max((_ar_year(r) for r in rows), default=0)
    cutoff = latest - years + 1 if years else None

    out: list[Filing] = []
    for row in rows:
        url = (row.get("PDFDownload") or "").strip()
        year = _ar_year(row)
        if not url or not year:
            continue
        if cutoff is not None and year < cutoff:
            continue
        out.append(Filing(
            news_id=f"AR-{scrip_code}-{year}",
            date=_ar_date(row, year),
            headline=f"Annual Report {year}",
            attachment=url, folder="annual-reports", category="Annual Reports",
        ))
    out.sort(key=lambda f: f.date, reverse=True)
    return out


def list_all_filings(scrip_code: str, specs: list[CategorySpec], years: int,
                     client: BSEClient, *, everything: bool = False) -> list[Filing]:
    """Both BSE filing sources as one listing, the overlap counted once.

    Announcements only carry annual reports from 2015 (LODR Reg. 34(1)); the
    archive carries them from 1997. Where a report is in both, the ANNOUNCEMENT
    entry wins — `already_have` keys on news_id, so preferring the archive's id
    would make every existing library re-download reports it already holds.

    The archive is only read when annual reports are actually wanted, and an
    archive outage degrades to announcements-only rather than failing the pull.
    """
    filings = list_filings(scrip_code, specs, years, client, everything=everything)
    if not (everything or any(s.key == "annual_report" for s in specs)):
        return filings

    have_attachments = {_attachment_id(f.attachment) for f in filings}
    # BSE serves the same annual report from its two systems under DIFFERENT
    # attachment GUIDs for some years (seen on Escorts FY2020-FY2023), so the
    # attachment alone is not enough. The filing date is identical to the day in
    # every observed overlap, and is the stable identity.
    have_dates = {f.date for f in filings if f.folder == "annual-reports"}
    try:
        archived = list_annual_reports(scrip_code, client, years=years)
    except FilingForgeError:
        return filings                      # archive down → keep what we have
    filings.extend(
        f for f in archived
        if _attachment_id(f.attachment) not in have_attachments
        and f.date not in have_dates
    )
    return filings


def _attachment_id(attachment: str) -> str:
    """Last path segment, lowercased — the one thing both sources share for the
    same document (a bare filename in announcements, the tail of a full URL in
    the archive)."""
    return attachment.rsplit("/", 1)[-1].strip().lower()


def _ar_year(row: dict) -> int:
    try:
        return int(str(row.get("Year") or "").strip())
    except ValueError:
        return 0


def _ar_date(row: dict, year: int) -> str:
    """BSE leaves Fld_AuthoriseDate null on the oldest reports. The date only drives
    ordering and the filename prefix — the year itself is in the headline — so the
    Indian financial-year end is a safe stand-in when the real one is missing."""
    authorised = (row.get("Fld_AuthoriseDate") or "").strip()
    return authorised[:10] if len(authorised) >= 10 else f"{year}-03-31"


def download_filing(filing: Filing, client: BSEClient) -> bytes:
    """Return validated PDF bytes. Verifies the %PDF magic.

    Announcement attachments are bare filenames and are tried against AttachHis
    then AttachLive; annual-report attachments already carry their own absolute
    URL and are fetched as-is. Raises DownloadError (friendly) if no real PDF.
    """
    if filing.attachment.startswith(("http://", "https://")):
        content = client.get_bytes(filing.attachment)
        if content[:5] == b"%PDF-":
            return content
        raise DownloadError(filing.headline or filing.attachment)
    for base in _PDF_BASES:
        content = client.get_bytes(base + filing.attachment)
        if content[:5] == b"%PDF-":
            return content
    raise DownloadError(filing.headline or filing.attachment)
