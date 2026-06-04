"""HTTP routes. Thin: parse → call engine/jobs → shape response. Grown across Tasks 3–7."""
from __future__ import annotations
from fastapi import APIRouter
from engine import __version__ as engine_version

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "version": engine_version}
