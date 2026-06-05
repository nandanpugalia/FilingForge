"""FilingForge engine — headless, UI-ready library builder for Indian company filings."""
__version__ = "0.2.0"

from .bse_client import BSEClient
from .resolver import resolve
from .library import build_library, refresh_library
from .models import Candidate, Filing, CategorySpec, CURATED, CURATED_BY_KEY, LibraryResult, slug
from .indexer import build_index, build_master_index, read_library
from .progress import ProgressEvent
from .errors import (
    FilingForgeError, CompanyNotFoundError, BSEUnavailableError, DownloadError,
)

__all__ = [
    "BSEClient", "resolve", "build_library", "refresh_library",
    "Candidate", "Filing", "CategorySpec", "CURATED", "CURATED_BY_KEY", "LibraryResult", "slug",
    "build_index", "build_master_index", "read_library", "ProgressEvent",
    "FilingForgeError", "CompanyNotFoundError", "BSEUnavailableError", "DownloadError",
]
