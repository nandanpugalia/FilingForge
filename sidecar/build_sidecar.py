#!/usr/bin/env python3
"""Build the FilingForge engine as a one-file PyInstaller binary and place it as the
Tauri sidecar — cross-platform (macOS / Windows / Linux), so CI can build it on every
runner. Mirrors sidecar/build.sh but handles the Windows `.exe` suffix + target triple.

Usage (from repo root, with the engine + api + pyinstaller installed):
    python sidecar/build_sidecar.py
Output:
    ui/src-tauri/binaries/filingforge-api-<triple>[.exe]   (the Tauri sidecar)
"""
from __future__ import annotations
import os, platform, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def target_triple() -> str:
    if os.environ.get("TARGET_TRIPLE"):
        return os.environ["TARGET_TRIPLE"]
    try:
        out = subprocess.run(["rustc", "-vV"], capture_output=True, text=True, check=True).stdout
        for line in out.splitlines():
            if line.startswith("host:"):
                return line.split()[1]
    except Exception:
        pass
    # fallbacks by OS/arch
    sysname, mach = platform.system(), platform.machine().lower()
    if sysname == "Darwin":
        return "aarch64-apple-darwin" if mach in ("arm64", "aarch64") else "x86_64-apple-darwin"
    if sysname == "Windows":
        return "x86_64-pc-windows-msvc"
    return "x86_64-unknown-linux-gnu"


def main() -> int:
    triple = target_triple()
    is_win = platform.system() == "Windows"
    print(f">> Target triple: {triple}")

    cmd = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile",
        "--name", "filingforge-api", "--paths", ".",
        "--collect-submodules", "uvicorn",
        "--collect-submodules", "engine",
        "--collect-submodules", "api",
        # Recursive collection is needed for runtime-selected adapters, but
        # must not drag the repository's pytest suites into the desktop app.
        "--exclude-module", "engine.tests",
        "--exclude-module", "api.tests",
        "--exclude-module", "pytest",
        "--exclude-module", "_pytest",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.logging",
        "--collect-all", "pydantic", "--collect-all", "pydantic_core",
        "sidecar/run_api.py",
    ]
    subprocess.run(cmd, cwd=ROOT, check=True)

    raw = ROOT / "dist" / ("filingforge-api.exe" if is_win else "filingforge-api")
    dest_dir = ROOT / "ui" / "src-tauri" / "binaries"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"filingforge-api-{triple}{'.exe' if is_win else ''}"
    shutil.copy2(raw, dest)
    if not is_win:
        dest.chmod(0o755)
    print(f">> Built sidecar: {dest} ({dest.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
