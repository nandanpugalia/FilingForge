"""FilingForge local API — thin FastAPI glue exposing the engine to the desktop UI."""
from .app import create_app

__all__ = ["create_app"]
