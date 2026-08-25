#!/usr/bin/env bash
# Build the FilingForge API as a single standalone executable (PyInstaller --onefile)
# and place it as a Tauri sidecar. Users need NO Python installed to run the result.
#
# Prereq: a venv at .venv with the engine + api packages (editable installed) plus
# fastapi, uvicorn[standard], httpx, pypdf, pydantic, and PyInstaller (6.x).
#
# Usage (from repo root):  ./sidecar/build.sh
#
# Output:
#   dist/filingforge-api                                  (raw one-file binary)
#   ui/src-tauri/binaries/filingforge-api-<triple>        (renamed Tauri sidecar)
#
# The sidecar name MUST be "<base>-<target-triple>" for Tauri to pick it up.
# On Apple Silicon the triple is aarch64-apple-darwin.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

VENV="${VENV:-./.venv}"
PYINSTALLER="$VENV/bin/pyinstaller"

# Resolve the Rust/Tauri target triple. Default to aarch64-apple-darwin (Apple Silicon).
TRIPLE="${TARGET_TRIPLE:-}"
if [ -z "$TRIPLE" ]; then
  if command -v rustc >/dev/null 2>&1; then
    TRIPLE="$(rustc -vV | awk '/^host:/{print $2}')"
  else
    TRIPLE="aarch64-apple-darwin"
  fi
fi
echo ">> Target triple: $TRIPLE"

# --- The FINAL working PyInstaller command ---------------------------------
# Notes on the flags that actually mattered:
#   --paths .                : engine/api are PEP 660 editable installs behind a
#                              custom __editable__ finder that PyInstaller cannot
#                              trace. Adding the repo root to the module search
#                              path lets PyInstaller find the source packages.
#   --collect-submodules ... : pull in all of uvicorn/engine/api submodules.
#   --hidden-import uvicorn.*: uvicorn picks protocol/loop/lifespan impls at
#                              runtime via strings, so they are invisible to the
#                              static graph and must be forced in.
#   --collect-all pydantic{,_core}: pydantic v2 + compiled core; needed by fastapi.
# fastapi / starlette / anyio / h11 / httpx / pypdf / click / sniffio / certifi
# all get pulled in transitively once api/engine are reachable — no extra flags
# were needed for them in this build.
"$PYINSTALLER" --noconfirm --onefile --name filingforge-api \
  --paths . \
  --collect-submodules uvicorn --collect-submodules engine --collect-submodules api \
  --exclude-module engine.tests --exclude-module api.tests \
  --exclude-module pytest --exclude-module _pytest \
  --hidden-import uvicorn.lifespan.on --hidden-import uvicorn.loops.auto \
  --hidden-import uvicorn.protocols.http.auto --hidden-import uvicorn.protocols.websockets.auto \
  --hidden-import uvicorn.logging \
  --collect-all pydantic --collect-all pydantic_core \
  sidecar/run_api.py

# --- Place + rename as the Tauri sidecar -----------------------------------
DEST_DIR="ui/src-tauri/binaries"
DEST="$DEST_DIR/filingforge-api-$TRIPLE"
mkdir -p "$DEST_DIR"
cp ./dist/filingforge-api "$DEST"
chmod +x "$DEST"

echo
echo ">> Built sidecar: $DEST"
ls -lh "$DEST"
echo ">> Done. Smoke-test with:  '$DEST' & sleep 7; curl -s localhost:8765/health; kill %1"
