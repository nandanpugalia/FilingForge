"""Minimal FilingForge engine example.

Run from an editable checkout after:

    pip install -e ".[api,dev]"
    python examples/python_api.py TANLA ./FilingForgeLibrary --years 3

This uses only public BSE filings and writes a local Markdown library.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from engine import BSEClient, CURATED, FilingForgeError, build_library, resolve


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a small FilingForge library.")
    parser.add_argument("company", help="Company name to resolve on BSE, e.g. TANLA")
    parser.add_argument("dest", nargs="?", default="./FilingForgeLibrary")
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument(
        "--everything",
        action="store_true",
        help="Download every filing type instead of the default high-signal set.",
    )
    args = parser.parse_args()

    client = BSEClient()
    try:
        candidates = resolve(args.company, client)
        chosen = next((c for c in candidates if c.is_primary), candidates[0])
        ticker = chosen.symbol or f"{chosen.company.split()[0].upper()}-{chosen.scrip_code}"
        specs = [] if args.everything else [spec for spec in CURATED if spec.default_on]

        print(f"Using: {chosen.company} ({chosen.scrip_code})")

        def progress(event):
            print(f"[{event.percent:3d}%] {event.message}")

        result = build_library(
            chosen.scrip_code,
            ticker,
            Path(args.dest),
            specs,
            args.years,
            client,
            on_progress=progress,
            everything=args.everything,
        )
        print(
            f"\nDone. {len(result.downloaded)} new, {len(result.skipped)} already present, "
            f"{len(result.failed)} skipped."
        )
        return 0
    except FilingForgeError as exc:
        print(exc.user_message)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
