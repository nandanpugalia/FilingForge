"""Frozen entrypoint for the FilingForge API (PyInstaller → Tauri sidecar). No args. Binds
127.0.0.1 only (loopback — the token gate depends on it) on the port the Rust shell chose and
passed via FF_PORT (falls back to 8765). This is the SHIPPED entry — keep it in sync with
api/server.py (the `python -m api` dev entry); both must read FF_PORT or the dynamic-port
feature is dead in the packaged app even though tests pass."""
import os
import uvicorn
from api.app import create_app

def main():
    port = int(os.environ.get("FF_PORT", "8765"))
    uvicorn.run(create_app(), host="127.0.0.1", port=port, log_level="warning")

if __name__ == "__main__":
    main()
