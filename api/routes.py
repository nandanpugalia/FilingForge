"""HTTP routes. Thin: parse → call engine/jobs → shape response. Grown across Tasks 3–7."""
from __future__ import annotations
from fastapi import APIRouter, Request, HTTPException
from engine import __version__ as engine_version
from engine.bse_client import BSEClient
from engine.resolver import resolve
from .jobs import run_build
from .schemas import ResolveRequest, CandidateOut, BuildRequest, JobCreated, JobStatusOut

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


@router.post("/build", status_code=202)
def start_build(req: BuildRequest, request: Request) -> dict:
    mgr = request.app.state.jobs
    job = mgr.create()
    work = run_build(req.scrip_code, req.ticker, req.dest, req.kinds, req.years)
    mgr.start(job, work)
    return JobCreated(job_id=job.id).model_dump()


@router.get("/build/{job_id}")
def build_status(job_id: str, request: Request) -> dict:
    job = request.app.state.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="unknown job")
    return JobStatusOut(job_id=job.id, status=job.status, progress=job.last_progress,
                        result=job.result, error=job.error).model_dump()
