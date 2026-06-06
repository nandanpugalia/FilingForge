"""uvicorn entrypoint: `python -m api` runs the local API on loopback only.
The Tauri sidecar (Plan 05) launches this; a non-technical user never sees it."""
from __future__ import annotations
import os
import uvicorn
from .app import create_app

HOST = "127.0.0.1"   # local-first: never bind 0.0.0.0 (token gate depends on loopback-only)
PORT = int(os.environ.get("FF_PORT", "8765"))


def main() -> None:
    uvicorn.run(create_app(), host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
