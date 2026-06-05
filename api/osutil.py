"""Open a folder in the OS file manager. Safe: validates the dir, then launches the
native opener. On Windows we use os.startfile — the documented API for "reveal in
Explorer" — which foregrounds reliably from a windowless sidecar process, unlike
shelling out to explorer.exe. On macOS/Linux we use a fixed argv list with no shell,
so a user-supplied path can never inject a command."""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path


def open_folder(path: str) -> None:
    # The UI sends paths with a literal "~" (e.g. the default library root). Path() does
    # NOT expand it, so expand here before validating/opening — otherwise the folder looks
    # "missing" and the button silently no-ops.
    p = Path(path).expanduser()
    if not p.exists():
        raise FileNotFoundError(path)
    if not p.is_dir():
        raise NotADirectoryError(path)
    if sys.platform.startswith("win"):
        os.startfile(str(p))  # type: ignore[attr-defined]  # Windows-only
        return
    argv = ["open", str(p)] if sys.platform == "darwin" else ["xdg-open", str(p)]
    subprocess.run(argv, shell=False, check=False)
