"""Open a folder in the OS file manager. Safe: validates the dir, launches with a fixed argv
list and no shell, so a user-supplied path can never inject a command."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path


def open_folder(path: str) -> None:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    if not p.is_dir():
        raise NotADirectoryError(path)
    if sys.platform == "darwin":
        argv = ["open", str(p)]
    elif sys.platform.startswith("win"):
        argv = ["explorer", str(p)]
    else:
        argv = ["xdg-open", str(p)]
    subprocess.run(argv, shell=False, check=False)
