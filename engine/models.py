"""Plain data the whole engine speaks in. CategorySpec replaces the old fixed FilingType enum:
each spec is an exact (category, subcategory) pair OR a (category, *) wildcard, and carries its
UI label, a stable key, and the on-disk folder it lands in."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional


_WIN_RESERVED = {"con", "prn", "aux", "nul",
                 *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}


def slug(text: str) -> str:
    """'Company Update' -> 'company-update'. Used to folder arbitrary BSE categories.
    Output is [a-z0-9-] only, never empty, never a Windows reserved device name."""
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if not s:
        return "other"
    if s in _WIN_RESERVED:
        return f"{s}-cat"
    return s


@dataclass(frozen=True)
class CategorySpec:
    """A filing category the user can pick. `subcategory=None` means 'whole category' (wildcard).
    `default_on` marks the high-signal categories that are pre-ticked in the UI — picking only
    these (instead of `everything`) is what stops a 5-year pull dumping 100s of postal ballots,
    routine board notices and minor 'company update' filings."""
    key: str
    label: str
    folder: str
    category: str
    subcategory: Optional[str] = None
    default_on: bool = False

    def matches(self, cat: str, sub: str) -> bool:
        if cat != self.category:
            return False
        return self.subcategory is None or sub == self.subcategory


CURATED: list[CategorySpec] = [
    CategorySpec("annual_report", "Annual Reports", "annual-reports", "Others", "Reg. 34 (1) Annual Report", default_on=True),
    CategorySpec("results", "Financial Results", "quarterly", "Result", "Financial Results", default_on=True),
    CategorySpec("investor_ppt", "Investor Presentations", "investor-ppts", "Company Update", "Investor Presentation", default_on=True),
    CategorySpec("concall", "Concall Transcripts", "concalls", "Company Update", "Earnings Call Transcript", default_on=True),
    CategorySpec("board_outcome", "Board-Meeting Outcomes", "board-meetings", "Board Meeting", "Outcome of Board Meeting"),
    CategorySpec("press", "Press / Media Releases", "press", "Company Update", "Press Release / Media Release"),
    CategorySpec("analyst_meet", "Analyst / Investor Meets", "analyst-meets", "Company Update", "Analyst / Investor Meet"),
    CategorySpec("corp_actions", "Dividends & Corp Actions", "corp-actions", "Corp. Action", None),
    CategorySpec("agm_egm", "AGM / EGM", "agm-egm", "AGM/EGM", None),
]
CURATED_BY_KEY: dict[str, CategorySpec] = {c.key: c for c in CURATED}


def default_category_keys() -> list[str]:
    """The pre-ticked high-signal category keys for a NEW library (sorted, stable)."""
    return sorted(c.key for c in CURATED if c.default_on)


@dataclass(frozen=True)
class Candidate:
    scrip_code: str
    company: str
    is_primary: bool = False
    isin: Optional[str] = None
    symbol: Optional[str] = None


@dataclass(frozen=True)
class Filing:
    news_id: str
    date: str
    headline: str
    attachment: str
    folder: str
    category: str


@dataclass(frozen=True)
class PendingDocument:
    """A substantive filing whose BSE attachment was only a cover letter.

    The original BSE identity is retained so a user-selected PDF can enter the
    ordinary organiser/converter/dedup path without becoming a second filing.
    """
    news_id: str
    date: str
    headline: str
    folder: str
    category: str
    expected_type: str
    expected_period: Optional[str]
    bse_url: str
    issuer_url: Optional[str]
    reason: str


@dataclass
class LibraryResult:
    downloaded: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    pending: list[PendingDocument] = field(default_factory=list)
    ready: int = 0
    cancelled: bool = False                 # user pressed Stop; library left consistent

    @property
    def total_attempted(self) -> int:
        return len(self.downloaded) + len(self.skipped) + len(self.failed) + len(self.pending)

    @property
    def ok(self) -> bool:
        return len(self.downloaded) > 0
