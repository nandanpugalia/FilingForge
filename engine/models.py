"""Plain data the whole engine speaks in. No behaviour beyond trivial helpers."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class FilingType(Enum):
    """The filing kinds v1 supports. `.bse` = the (CATEGORYNAME, SUBCATNAME) BSE filter
    confirmed in the spike; `.folder` = the clean per-type subfolder the user sees."""
    ANNUAL_REPORT = ("Others", "Reg. 34 (1) Annual Report", "annual-reports")
    RESULTS = ("Result", "Financial Results", "quarterly")
    INVESTOR_PPT = ("Company Update", "Investor Presentation", "investor-ppts")
    CONCALL = ("Company Update", "Earnings Call Transcript", "concalls")

    def __init__(self, category: str, subcategory: str, folder: str):
        self._cat = category
        self._sub = subcategory
        self.folder = folder

    @property
    def bse(self) -> tuple[str, str]:
        return (self._cat, self._sub)


@dataclass(frozen=True)
class Candidate:
    """A company match from the resolver. UI shows a pick-list; `is_primary` is pre-selected."""
    scrip_code: str
    company: str
    is_primary: bool = False


@dataclass(frozen=True)
class Filing:
    """One downloadable filing. `news_id` (BSE NEWSID) is the stable dedup key."""
    news_id: str
    date: str            # YYYY-MM-DD
    headline: str
    attachment: str      # ATTACHMENTNAME, e.g. "<guid>.pdf"
    kind: FilingType


@dataclass
class LibraryResult:
    """Outcome of a build/refresh. Partial success is normal; the folder is always valid."""
    downloaded: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)   # already present (incremental dedup)
    failed: list[str] = field(default_factory=list)     # download/convert failed, folder intact

    @property
    def total_attempted(self) -> int:
        return len(self.downloaded) + len(self.skipped) + len(self.failed)

    @property
    def ok(self) -> bool:
        return len(self.downloaded) > 0
