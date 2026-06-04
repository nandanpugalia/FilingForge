"""FilingForge local API — thin FastAPI glue exposing the engine to the desktop UI."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .app import create_app

__all__ = ["create_app"]


def __getattr__(name: str):
    # Lazy re-export so importing subpackages (api.schemas, api.jobs) doesn't require
    # api.app to exist yet (it lands in a later task).
    if name == "create_app":
        from .app import create_app
        return create_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
