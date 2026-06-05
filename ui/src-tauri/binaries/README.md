# Tauri sidecar binaries

This directory holds the **FilingForge API sidecar** — a single standalone
executable that bundles the FastAPI app + engine so the desktop app can ship
with **no Python required on the user's machine**.

The binaries themselves are **git-ignored** (each is ~18 MB and is a build
output, not source). Only this README is tracked. Rebuild them from source.

## Naming

Tauri requires sidecars to be named `<base>-<target-triple>`. The base is
`filingforge-api`, so on Apple Silicon the file must be exactly:

```
filingforge-api-aarch64-apple-darwin
```

(On an Intel Mac it would be `filingforge-api-x86_64-apple-darwin`, etc.)

## How to (re)build

From the repo root, with the project venv (`.venv`) active/available:

```bash
./sidecar/build.sh
```

That script runs the exact PyInstaller command below and then copies +
renames the result into this directory. Equivalent manual command:

```bash
./.venv/bin/pyinstaller --noconfirm --onefile --name filingforge-api \
  --paths . \
  --collect-submodules uvicorn --collect-submodules engine --collect-submodules api \
  --hidden-import uvicorn.lifespan.on --hidden-import uvicorn.loops.auto \
  --hidden-import uvicorn.protocols.http.auto --hidden-import uvicorn.protocols.websockets.auto \
  --hidden-import uvicorn.logging \
  --collect-all pydantic --collect-all pydantic_core \
  sidecar/run_api.py

cp ./dist/filingforge-api ui/src-tauri/binaries/filingforge-api-aarch64-apple-darwin
chmod +x ui/src-tauri/binaries/filingforge-api-aarch64-apple-darwin
```

### Why `--paths .` matters

`engine` and `api` are installed as **PEP 660 editable** packages, exposed
through a custom `__editable__` import finder that PyInstaller cannot trace
statically. Without `--paths .` the frozen binary fails at runtime with
`ModuleNotFoundError: No module named 'api'`. Pointing PyInstaller at the repo
root lets it find the real source packages.

## What it does

Run with **no arguments**, the binary starts the FastAPI app via uvicorn on
`127.0.0.1:8765` — identical to `python -m api`. Smoke test:

```bash
./filingforge-api-aarch64-apple-darwin &
sleep 7
curl -s localhost:8765/health
# {"status":"ok","version":"0.2.0"}
kill %1
```

## Startup time

This is a PyInstaller **one-file** build, so on launch it unpacks itself to a
temp dir before the server comes up. Cold start to a serving `/health` is
roughly **6 seconds** on an M-series Mac (bundled pydantic_core + fastapi +
uvicorn import chain). The app should **poll `/health`** until it returns 200
rather than assume the sidecar is instantly ready. (A one-dir build would start
faster but ships many files instead of one; one-file was chosen for clean
distribution.)
