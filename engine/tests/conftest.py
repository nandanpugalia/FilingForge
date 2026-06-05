"""Shared test helpers. No network: all BSE I/O is faked via httpx.MockTransport."""
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
