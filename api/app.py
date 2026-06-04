"""App factory. Local-first: CORS limited to the desktop/dev origins; one shared JobManager;
engine errors rendered friendly. uvicorn binds loopback (see server.py)."""
from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from engine.errors import FilingForgeError
from .errors import filingforge_exception_handler
from .jobs import JobManager
from .routes import router

_ALLOWED_ORIGINS = [
    "http://localhost:5173", "http://127.0.0.1:5173",
    "tauri://localhost", "https://tauri.localhost",
]


def create_app() -> FastAPI:
    app = FastAPI(title="FilingForge Local API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware, allow_origins=_ALLOWED_ORIGINS, allow_methods=["*"], allow_headers=["*"],
    )
    app.state.jobs = JobManager()
    app.add_exception_handler(FilingForgeError, filingforge_exception_handler)
    app.include_router(router)
    return app
