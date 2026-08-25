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
from engine.organiser import company_dir
from engine.pending import import_pending_pdf, list_pending
from engine.skills import list_imported_skills, import_skill, save_skill_content, skills_dir
from .jobs import run_build, JOB_DONE_SENTINEL
from .osutil import open_folder
from .schemas import (ResolveRequest, CandidateOut, BuildRequest, JobCreated, JobStatusOut,
                      OpenFolderRequest, ImportSkillRequest, InstallSkillRequest,
                      PendingDocumentOut, PendingImportRequest, PendingImportOut)

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
    request.app.state.library_root = req.dest
    job = mgr.create()
    work = run_build(req.scrip_code, req.ticker, req.dest, req.everything, req.categories, req.years,
                     should_cancel=job.cancel_event.is_set)
    mgr.start(job, work)
    return JobCreated(job_id=job.id).model_dump()


@router.post("/preview")
def preview_build(req: BuildRequest) -> dict:
    """List-only: how many filings the chosen scope would fetch (by category) and how many are
    already in the library. No downloads — the user approves before anything is pulled."""
    from engine.library import preview_library
    from engine.models import CURATED_BY_KEY
    specs = [CURATED_BY_KEY[k] for k in req.categories]
    client = BSEClient()
    try:
        return preview_library(req.scrip_code, Path(req.dest).expanduser(), req.ticker, specs,
                               req.years, client, everything=req.everything)
    finally:
        client.close()


@router.post("/build/{job_id}/cancel")
def cancel_build(job_id: str, request: Request) -> dict:
    if not request.app.state.jobs.cancel(job_id):
        raise HTTPException(status_code=404, detail="unknown job")
    return {"ok": True}


@router.get("/library")
def library(root: str, request: Request) -> dict:
    request.app.state.library_root = root
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


@router.get("/skills")
def skills() -> dict:
    """Imported skills from ~/.filingforge/skills/. Built-in skills ship in the UI; the app
    merges the two. Premium packs arrive here via /skills/import (the revenue seam)."""
    return {"skills": list_imported_skills(skills_dir())}


@router.post("/skills/import")
def skills_import(req: ImportSkillRequest) -> dict:
    from pathlib import Path as _P
    skill = import_skill(_P(req.path), skills_dir())   # SkillImportError → 400 via handler
    return {"skill": skill}


@router.post("/skills/install")
def skills_install(req: InstallSkillRequest) -> dict:
    """Install a skill that arrived as md TEXT (a paid pack the app fetched from the Worker).
    Writes it into ~/.filingforge/skills/ under a safe slug → appears in GET /skills like any
    imported skill. SkillImportError (bad name) → 400 via handler."""
    skill = save_skill_content(req.name, req.content, skills_dir())
    return {"skill": skill}


@router.post("/open-folder")
def open_result_folder(req: OpenFolderRequest) -> dict:
    try:
        open_folder(req.path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="That folder doesn't exist.")
    except NotADirectoryError:
        raise HTTPException(status_code=400, detail="That path isn't a folder.")
    return {"ok": True}


@router.get("/pending")
def pending_documents(root: str, ticker: str) -> dict:
    company = company_dir(Path(root).expanduser(), ticker)
    return {
        "pending": [PendingDocumentOut(**item.__dict__).model_dump()
                    for item in list_pending(company)]
    }


@router.post("/pending/import")
def pending_import(req: PendingImportRequest) -> dict:
    company = company_dir(Path(req.root).expanduser(), req.ticker)
    destination = import_pending_pdf(company, req.news_id, Path(req.path).expanduser())
    remaining = [PendingDocumentOut(**item.__dict__) for item in list_pending(company)]
    return PendingImportOut(
        news_id=req.news_id,
        destination=str(destination),
        pending=remaining,
    ).model_dump()
