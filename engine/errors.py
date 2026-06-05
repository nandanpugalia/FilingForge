"""Structured errors. Every error carries a non-technical `.user_message` the UI can show
directly — the raw technical string stays in `str(err)` for logs only."""
from __future__ import annotations


class FilingForgeError(Exception):
    """Base. `user_message` is safe to display to a non-technical end user."""

    def __init__(self, technical: str, user_message: str = "Something went wrong."):
        super().__init__(technical)
        self.user_message = user_message


class CompanyNotFoundError(FilingForgeError):
    def __init__(self, name: str):
        super().__init__(
            technical=f"no BSE match for {name!r}",
            user_message=f"We couldn't find a company called “{name}” on BSE. "
                         "Check the spelling and try again.",
        )


class BSEUnavailableError(FilingForgeError):
    def __init__(self, technical: str):
        super().__init__(
            technical=technical,
            user_message="BSE isn't responding right now. Please try again in a moment.",
        )


class DownloadError(FilingForgeError):
    def __init__(self, doc_label: str):
        super().__init__(
            technical=f"download failed: {doc_label}",
            user_message=f"Couldn't download “{doc_label}”. It was skipped; "
                         "the rest of your library is fine.",
        )


class SkillImportError(FilingForgeError):
    """A skill .md couldn't be imported (missing file, wrong type). A client mistake → 400."""
