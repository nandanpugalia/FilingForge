"""HTTP routes. Thin: parse → call engine/jobs → shape response. Grown across Tasks 3–7."""
from __future__ import annotations
from fastapi import APIRouter
from engine import __version__ as engine_version
from engine.bse_client import BSEClient
from engine.resolver import resolve
from .schemas import ResolveRequest, CandidateOut

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "version": engine_version}


@router.post("/resolve")
def resolve_company(req: ResolveRequest) -> dict:
    client = BSEClient()
    try:
        candidates = resolve(req.company, client)   # may raise FilingForgeError → handler
    finally:
        client.close()
    return {"candidates": [CandidateOut(scrip_code=c.scrip_code, company=c.company,
                                        is_primary=c.is_primary).model_dump()
                           for c in candidates]}
