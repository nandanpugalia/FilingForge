"""App factory. Local-first: CORS limited to the desktop/dev origins; one shared JobManager;
engine errors rendered friendly. uvicorn binds loopback (see server.py)."""
from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from engine.errors import FilingForgeError
from .errors import filingforge_exception_handler
from .jobs import JobManager
from .routes import router

# The engine binds 127.0.0.1 (loopback only — see server.py), so no REMOTE host can
# reach it. But the user's OWN browser — or a malicious local web page they visit while
# the app is running — can still POST to 127.0.0.1:8765 (/build, /open-folder). A wildcard
# `*` would let any internet origin's preflighted request through. So we gate by a regex
# that matches every real webview origin across OSes WITHOUT pinning a scheme we can't
# verify per-OS, while rejecting arbitrary internet sites:
#   tauri://localhost            macOS / Linux (Tauri v2 webview)
#   http(s)://tauri.localhost    Windows / Android (scheme varies by version)
#   http://localhost:<port>      dev (vite)
#   http://127.0.0.1:<port>      dev
_ALLOWED_ORIGIN_REGEX = (
    r"^(tauri://localhost"
    r"|https?://tauri\.localhost"
    r"|http://localhost:\d+"
    r"|http://127\.0\.0\.1:\d+)$"
)


def create_app() -> FastAPI:
    app = FastAPI(title="FilingForge Local API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware, allow_origin_regex=_ALLOWED_ORIGIN_REGEX,
        allow_methods=["*"], allow_headers=["*"],
    )
    app.state.jobs = JobManager()
    app.add_exception_handler(FilingForgeError, filingforge_exception_handler)

    from starlette.exceptions import HTTPException as StarletteHTTPException
    from fastapi.responses import JSONResponse

    async def _http_friendly(request, exc: StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code,
                            content={"user_message": str(exc.detail)})
    app.add_exception_handler(StarletteHTTPException, _http_friendly)

    app.include_router(router)
    return app
