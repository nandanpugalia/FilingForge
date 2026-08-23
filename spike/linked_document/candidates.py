from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin, urlsplit

from .models import Candidate, DocumentContext

_FY_RE = re.compile(
    r"(?:\bfy\b|financial\s+year)\s*[:\-]?\s*(20\d{2})\s*[-/]\s*(?:20)?(\d{2})",
    re.IGNORECASE,
)
_QUARTER_END_RE = re.compile(
    r"\b(march|june|september|december)\s+(?:3[01]|[12]?\d)(?:st|nd|rd|th)?\s*,?\s*(20\d{2})",
    re.IGNORECASE,
)
_QUARTER_END_DAY_FIRST_RE = re.compile(
    r"\b(?:3[01]|[12]?\d)(?:st|nd|rd|th)?\s+(march|june|september|december)\s*,?\s*(20\d{2})",
    re.IGNORECASE,
)
_TYPE_TERMS = {
    "annual-reports": ("annual report",),
    "concalls": ("transcript", "concall", "conference call", "earnings call"),
    "investor-ppts": ("investor presentation", "earnings presentation", "results presentation"),
    "quarterly": ("financial result", "quarterly result", "quarterly results"),
}
_MINIMUM_SCORE = 9


@dataclass(frozen=True)
class CandidateScore:
    type_score: int
    period_score: int
    date_score: int

    @property
    def total(self) -> int:
        return self.type_score + self.period_score + self.date_score


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: list[tuple[str, str]] = []
        self._href: str | None = None
        self._label: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        values = dict(attrs)
        self._href = values.get("href")
        self._label = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._label.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, " ".join("".join(self._label).split())))
            self._href = None
            self._label = []


def parse_html_candidates(html: bytes, landing_url: str) -> tuple[Candidate, ...]:
    parser = _AnchorParser()
    parser.feed(html.decode("utf-8", errors="replace"))
    found: list[Candidate] = []
    seen: set[str] = set()
    for href, label in parser.anchors:
        absolute, _fragment = urldefrag(urljoin(landing_url, href))
        parsed = urlsplit(absolute)
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            continue
        if not parsed.path.lower().endswith(".pdf"):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        found.append(Candidate(url=absolute, label=label, source="html"))
    return tuple(found)


def infer_period_tokens(context: DocumentContext, cover_text: str) -> frozenset[str]:
    source = f"{context.headline}\n{cover_text}"
    tokens: set[str] = set()
    for match in _FY_RE.finditer(source):
        start_year = int(match.group(1))
        end_two = int(match.group(2))
        end_year = (start_year // 100) * 100 + end_two
        if end_year < start_year:
            end_year += 100
        tokens.update(_fy_tokens(start_year, end_year))

    quarter_by_month = {"june": 1, "september": 2, "december": 3, "march": 4}
    quarter_ends = [
        (match.group(1).lower(), int(match.group(2)))
        for pattern in (_QUARTER_END_RE, _QUARTER_END_DAY_FIRST_RE)
        for match in pattern.finditer(source)
    ]
    for month, calendar_year in quarter_ends:
        quarter = quarter_by_month[month]
        fy_end = calendar_year if month == "march" else calendar_year + 1
        fy_start = fy_end - 1
        tokens.update(_fy_tokens(fy_start, fy_end))
        tokens.add(f"q{quarter}fy{fy_end % 100:02d}")
        tokens.add(f"q{quarter}fy{fy_start}{fy_end % 100:02d}")
    return frozenset(tokens)


def score_candidate(
    context: DocumentContext,
    cover_text: str,
    candidate: Candidate,
) -> CandidateScore:
    searchable = f"{candidate.label} {candidate.url}"
    normalized_words = " ".join(re.sub(r"[^a-z0-9]+", " ", searchable.lower()).split())
    compact = re.sub(r"[^a-z0-9]", "", searchable.lower())

    desired_terms = _TYPE_TERMS.get(context.folder, ())
    if any(term in normalized_words for term in desired_terms):
        type_score = 6
    elif any(
        term in normalized_words
        for folder, terms in _TYPE_TERMS.items()
        if folder != context.folder
        for term in terms
    ):
        type_score = -10
    else:
        type_score = 0

    period_tokens = infer_period_tokens(context, cover_text)
    quarter_tokens = {token for token in period_tokens if token.startswith("q")}
    exact_tokens = quarter_tokens or period_tokens
    period_score = 5 if any(token in compact for token in exact_tokens) else 0
    context_years = set(re.findall(r"20\d{2}", f"{context.headline} {cover_text}"))
    date_score = 2 if context_years and any(year in compact for year in context_years) else 0
    return CandidateScore(type_score=type_score, period_score=period_score, date_score=date_score)


def select_unique_candidate(
    context: DocumentContext,
    cover_text: str,
    candidates: tuple[Candidate, ...] | list[Candidate],
) -> Candidate | None:
    if not candidates:
        return None
    scored = [(score_candidate(context, cover_text, candidate).total, candidate) for candidate in candidates]
    best = max(score for score, _candidate in scored)
    winners = [candidate for score, candidate in scored if score == best]
    if best < _MINIMUM_SCORE or len(winners) != 1:
        return None
    return winners[0]


def _fy_tokens(start_year: int, end_year: int) -> set[str]:
    start_two = start_year % 100
    end_two = end_year % 100
    return {
        f"fy{start_year}{end_two:02d}",
        f"fy{end_two:02d}",
        f"{start_year}{end_two:02d}",
        f"{start_year}{end_year}",
        f"{start_two:02d}{end_two:02d}",
    }
