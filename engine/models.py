"""Plain data the whole engine speaks in. CategorySpec replaces the old fixed FilingType enum:
each spec is an exact (category, subcategory) pair OR a (category, *) wildcard, and carries its
UI label, a stable key, and the on-disk folder it lands in."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional


def slug(text: str) -> str:
    """'Company Update' -> 'company-update'. Used to folder arbitrary BSE categories."""
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "other"


@dataclass(frozen=True)
class CategorySpec:
    """A filing category the user can pick. `subcategory=None` means 'whole category' (wildcard)."""
    key: str
    label: str
    folder: str
    category: str
    subcategory: Optional[str] = None

    def matches(self, cat: str, sub: str) -> bool:
        if cat != self.category:
            return False
        return self.subcategory is None or sub == self.subcategory


CURATED: list[CategorySpec] = [
    CategorySpec("annual_report", "Annual Reports", "annual-reports", "Others", "Reg. 34 (1) Annual Report"),
    CategorySpec("results", "Financial Results", "quarterly", "Result", "Financial Results"),
    CategorySpec("investor_ppt", "Investor Presentations", "investor-ppts", "Company Update", "Investor Presentation"),
    CategorySpec("concall", "Concall Transcripts", "concalls", "Company Update", "Earnings Call Transcript"),
    CategorySpec("board_outcome", "Board-Meeting Outcomes", "board-meetings", "Board Meeting", "Outcome of Board Meeting"),
    CategorySpec("press", "Press / Media Releases", "press", "Company Update", "Press Release / Media Release"),
    CategorySpec("analyst_meet", "Analyst / Investor Meets", "analyst-meets", "Company Update", "Analyst / Investor Meet"),
    CategorySpec("corp_actions", "Dividends & Corp Actions", "corp-actions", "Corp. Action", None),
    CategorySpec("agm_egm", "AGM / EGM", "agm-egm", "AGM/EGM", None),
]
CURATED_BY_KEY: dict[str, CategorySpec] = {c.key: c for c in CURATED}


@dataclass(frozen=True)
class Candidate:
    scrip_code: str
    company: str
    is_primary: bool = False
    isin: Optional[str] = None


@dataclass(frozen=True)
class Filing:
    news_id: str
    date: str
    headline: str
    attachment: str
    folder: str
    category: str


@dataclass
class LibraryResult:
    downloaded: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    @property
    def total_attempted(self) -> int:
        return len(self.downloaded) + len(self.skipped) + len(self.failed)

    @property
    def ok(self) -> bool:
        return len(self.downloaded) > 0
