#!/usr/bin/env python3
"""Fail before packaging when the app manifests or release tag disagree."""
from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path


_TAG_RE = re.compile(
    r"^v(?P<version>\d+\.\d+\.\d+)(?:-[0-9A-Za-z][0-9A-Za-z.-]*)?$"
)


class ReleaseVersionError(ValueError):
    pass


def validate_release(root: Path, tag: str | None) -> str:
    root = Path(root)
    tauri_path = root / "ui" / "src-tauri" / "tauri.conf.json"
    cargo_path = root / "ui" / "src-tauri" / "Cargo.toml"
    tauri_version = str(json.loads(tauri_path.read_text(encoding="utf-8"))["version"])
    cargo_version = str(tomllib.loads(cargo_path.read_text(encoding="utf-8"))["package"]["version"])

    if tauri_version != cargo_version:
        raise ReleaseVersionError(
            f"manifest versions differ: tauri={tauri_version}, cargo={cargo_version}"
        )
    if tag is not None:
        match = _TAG_RE.fullmatch(tag)
        if match is None:
            raise ReleaseVersionError(f"not a valid release tag: {tag!r}")
        tag_version = match.group("version")
        if tag_version != tauri_version:
            raise ReleaseVersionError(
                f"tag version {tag_version} does not match app version {tauri_version}"
            )
    return tauri_version


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--tag")
    args = parser.parse_args(argv)
    try:
        version = validate_release(args.root, args.tag)
    except (OSError, KeyError, json.JSONDecodeError, tomllib.TOMLDecodeError,
            ReleaseVersionError) as exc:
        print(f"release version check failed: {exc}", file=sys.stderr)
        return 1
    suffix = f" matches {args.tag}" if args.tag else " is consistent across manifests"
    print(f"FilingForge {version}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
