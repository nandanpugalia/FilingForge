import pytest
from engine.errors import (
    FilingForgeError, CompanyNotFoundError, BSEUnavailableError, DownloadError,
)


def test_base_carries_user_message_distinct_from_technical():
    err = FilingForgeError("raw httpx 503 detail", user_message="Something went wrong.")
    assert err.user_message == "Something went wrong."
    assert "503" in str(err)  # technical detail preserved for logs


def test_company_not_found_has_friendly_default_message():
    err = CompanyNotFoundError("RELiNCE")
    assert "RELiNCE" in err.user_message
    assert "couldn't find" in err.user_message.lower()
    assert isinstance(err, FilingForgeError)


def test_bse_unavailable_is_friendly_and_suggests_retry():
    err = BSEUnavailableError("connect timeout")
    assert "BSE" in err.user_message
    assert "try again" in err.user_message.lower()


def test_download_error_names_the_document():
    err = DownloadError("Annual Report 2024")
    assert "Annual Report 2024" in err.user_message
