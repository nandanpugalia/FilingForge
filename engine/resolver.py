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
_STRONG = re.compile(r"<strong>([A-Z0-9&.\-]{2,})</strong>")   # bold ticker within a row


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
        st = _STRONG.search(block)
        if st:
            symbol_by_code[m.group(1)] = st.group(1)
    sel = _SELECTED.search(html)
    primary = sel.group(1) if sel else pairs[0][0]
    return [Candidate(scrip_code=code, company=label, is_primary=(code == primary),
                      isin=isin_by_code.get(code), symbol=symbol_by_code.get(code))
            for code, label in pairs]
