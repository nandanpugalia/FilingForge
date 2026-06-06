import os
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()


def _root(request: Request) -> Path:
    # Prefer the root the UI registered at runtime (set on /library and /build);
    # fall back to the FF_LIBRARY_ROOT env (used by tests). Resolve for containment checks.
    # Fail CLOSED if neither is set: an empty path would resolve to the process cwd and
    # serve files from there — so refuse rather than silently widen the served root.
    root = getattr(request.app.state, "library_root", None) or os.environ.get("FF_LIBRARY_ROOT")
    if not root:
        raise HTTPException(503, "library root not configured")
    return Path(str(root)).expanduser().resolve()


@router.get("/lib/{rel:path}")
def serve(rel: str, request: Request):
    # Token is the security boundary; everything below is defense-in-depth.
    # Fail CLOSED: with no token configured (FF_TOKEN unset) we serve nothing, so a
    # mis-launched sidecar can never expose the library rather than a None==None match.
    expected = os.environ.get("FF_TOKEN")
    if not expected or request.query_params.get("token") != expected:
        raise HTTPException(403, "forbidden")
    if rel == "" or rel.endswith("/"):
        raise HTTPException(404, "no directory listing")
    root = _root(request)
    raw = root / rel
    # Symlink guard BEFORE resolve(): resolve() would dereference the link and hide the escape.
    if raw.is_symlink():
        raise HTTPException(404, "not found")
    target = raw.resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise HTTPException(404, "not found")
    resp = FileResponse(target)
    resp.headers["Access-Control-Allow-Origin"] = "null"   # deny cross-origin reads
    return resp
