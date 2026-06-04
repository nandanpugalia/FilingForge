"""FilingForge engine — headless, UI-ready library builder for Indian company filings."""
__version__ = "0.1.0"

from .bse_client import BSEClient
from .resolver import resolve
from .library import build_library, refresh_library
from .models import Candidate, Filing, FilingType, LibraryResult
from .progress import ProgressEvent
from .errors import (
    FilingForgeError, CompanyNotFoundError, BSEUnavailableError, DownloadError,
)

__all__ = [
    "BSEClient", "resolve", "build_library", "refresh_library",
    "Candidate", "Filing", "FilingType", "LibraryResult", "ProgressEvent",
    "FilingForgeError", "CompanyNotFoundError", "BSEUnavailableError", "DownloadError",
]
