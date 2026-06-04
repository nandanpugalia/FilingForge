"""Name → BSE scrip-code candidates via PeerSmartSearch (confirmed in spike).
Never guesses: returns ALL matches with the BSE-preferred one flagged is_primary, so the UI
shows a pick-list. Disambiguation is a UI decision, not a silent engine one."""
from __future__ import annotations
import re
from .bse_client import BSEClient
from .models import Candidate
from .errors import CompanyNotFoundError

URL = "https://api.bseindia.com/BseIndiaAPI/api/PeerSmartSearch/w"
_LICLICK = re.compile(r"liclick\('(\d{6})','([^']+)'\)")
_SELECTED = re.compile(r"quotemenuselect[^>]*?liclick\('(\d{6})'")


def resolve(name: str, client: BSEClient) -> list[Candidate]:
    html = client.get_text(URL, {"Type": "EQ", "text": name})
    pairs = _LICLICK.findall(html)
    if not pairs:
        raise CompanyNotFoundError(name)
    sel = _SELECTED.search(html)
    primary = sel.group(1) if sel else pairs[0][0]
    return [Candidate(scrip_code=code, company=label, is_primary=(code == primary))
            for code, label in pairs]
