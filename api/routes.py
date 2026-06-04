"""HTTP routes. Thin: parse → call engine/jobs → shape response. Grown across Tasks 3–7."""
from __future__ import annotations
import json
import queue
from pathlib import Path
import anyio
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from engine import __version__ as engine_version
from engine.bse_client import BSEClient
from engine.resolver import resolve
from engine.indexer import read_library
from .jobs import run_build, JOB_DONE_SENTINEL
from .osutil import open_folder
from .schemas import ResolveRequest, CandidateOut, BuildRequest, JobCreated, JobStatusOut, OpenFolderRequest

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
                                        is_primary=c.is_primary, isin=c.isin,
                                        symbol=c.symbol).model_dump()
                           for c in candidates]}


@router.post("/build", status_code=202)
def start_build(req: BuildRequest, request: Request) -> dict:
    mgr = request.app.state.jobs
    job = mgr.create()
    work = run_build(req.scrip_code, req.ticker, req.dest, req.everything, req.categories, req.years)
    mgr.start(job, work)
    return JobCreated(job_id=job.id).model_dump()


@router.get("/library")
def library(root: str) -> dict:
    return {"companies": read_library(Path(root))}


@router.get("/build/{job_id}")
def build_status(job_id: str, request: Request) -> dict:
    job = request.app.state.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="unknown job")
    return JobStatusOut(job_id=job.id, status=job.status, progress=job.last_progress,
                        result=job.result, error=job.error).model_dump()


@router.get("/build/{job_id}/events")
def build_events(job_id: str, request: Request) -> StreamingResponse:
    job = request.app.state.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="unknown job")

    async def stream():
        while True:
            if await request.is_disconnected():
                return
            try:
                ev = await anyio.to_thread.run_sync(lambda: job.events.get(timeout=1.0))
            except queue.Empty:
                continue   # no event yet; loop back to re-check disconnect
            if ev is JOB_DONE_SENTINEL:
                tail = {"status": job.status, "result": job.result, "error": job.error}
                yield f"data: {json.dumps(tail)}\n\nevent: end\ndata: end\n\n"
                return
            yield f"data: {json.dumps(ev)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.post("/open-folder")
def open_result_folder(req: OpenFolderRequest) -> dict:
    try:
        open_folder(req.path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="That folder doesn't exist.")
    except NotADirectoryError:
        raise HTTPException(status_code=400, detail="That path isn't a folder.")
    return {"ok": True}
