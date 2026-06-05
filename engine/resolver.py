"""Name → BSE scrip-code candidates via PeerSmartSearch (confirmed in spike).
Never guesses: returns ALL matches with the BSE-preferred one flagged is_primary, so the UI
shows a pick-list. Also surfaces ISIN per candidate when present in the row."""
from __future__ import annotations
import re
from .bse_client import BSEClient
from .models import Candidate
from .errors import CompanyNotFoundError

URL = "https://api.bseindia.com/BseIndiaAPI/api/PeerSmartSearch/w"
_LICLICK = re.compile(r"liclick\('(\d{6})','([^']+)'\)")
_SELECTED = re.compile(r"quotemenuselect[^>]*?liclick\('(\d{6})'")
_LI = re.compile(r"<li\b.*?</li>", re.S)            # each result row
_ISIN = re.compile(r"\b(IN[EF][0-9A-Z]{9})\b")      # ISIN within a row
_SPAN = re.compile(r"<span>(.*?)</span>", re.S)     # the row's "<TICKER> <ISIN> <code>" span


def _ticker_from_span(block: str) -> str | None:
    """The real BSE symbol is the FIRST token of the <span> (e.g. '<strong>TITA</strong>N&nbsp;
    INE…&nbsp;500114' → 'TITAN'). Do NOT use the <strong> match — PeerSmartSearch bolds the typed
    query substring, so that would give 'TITA' for the query 'tita'."""
    m = _SPAN.search(block)
    if not m:
        return None
    text = re.sub(r"<[^>]+>", "", m.group(1)).replace("&nbsp;", " ").replace("&#160;", " ")
    toks = text.split()
    if toks and re.fullmatch(r"[A-Z0-9&.\-]{1,20}", toks[0]):
        return toks[0]
    return None


def resolve(name: str, client: BSEClient) -> list[Candidate]:
    html = client.get_text(URL, {"Type": "EQ", "text": name})
    pairs = _LICLICK.findall(html)
    if not pairs:
        raise CompanyNotFoundError(name)
    isin_by_code: dict[str, str] = {}
    symbol_by_code: dict[str, str] = {}
    for block in _LI.findall(html):
        m = _LICLICK.search(block)
        if not m:
            continue
        i = _ISIN.search(block)
        if i:
            isin_by_code[m.group(1)] = i.group(1)
        sym = _ticker_from_span(block)
        if sym:
            symbol_by_code[m.group(1)] = sym
    sel = _SELECTED.search(html)
    primary = sel.group(1) if sel else pairs[0][0]
    return [Candidate(scrip_code=code, company=label, is_primary=(code == primary),
                      isin=isin_by_code.get(code), symbol=symbol_by_code.get(code))
            for code, label in pairs]
