"""Frozen entrypoint for the FilingForge API (PyInstaller → Tauri sidecar). No args; serves on 127.0.0.1:8765."""
import uvicorn
from api.app import create_app

def main():
    uvicorn.run(create_app(), host="127.0.0.1", port=8765, log_level="warning")

if __name__ == "__main__":
    main()
