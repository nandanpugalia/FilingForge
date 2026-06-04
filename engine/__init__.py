"""FilingForge engine — headless, UI-ready library builder for Indian company filings."""
__version__ = "0.1.0"

from .models import Candidate, Filing, CategorySpec, LibraryResult, CURATED, CURATED_BY_KEY, slug
from .progress import ProgressEvent
from .errors import (
    FilingForgeError, CompanyNotFoundError, BSEUnavailableError, DownloadError,
)

# NOTE (feat/engine-v02 refactor in progress): bse_client/resolver/library and friends
# still reference the removed FilingType and are being migrated in later tasks. Import them
# lazily so the already-migrated `engine.models` surface stays importable meanwhile.
try:  # pragma: no cover - transitional during refactor
    from .bse_client import BSEClient
    from .resolver import resolve
    from .library import build_library, refresh_library
except ImportError:  # pragma: no cover - expected until fetcher/library are migrated
    pass

__all__ = [
    "BSEClient", "resolve", "build_library", "refresh_library",
    "Candidate", "Filing", "CategorySpec", "LibraryResult", "CURATED", "CURATED_BY_KEY", "slug",
    "ProgressEvent",
    "FilingForgeError", "CompanyNotFoundError", "BSEUnavailableError", "DownloadError",
]
