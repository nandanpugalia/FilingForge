"""Dogfood CLI: `python -m engine "TANLA" ./MyLibrary --years 5`.
This is for the maintainer; the real product is the Plan 04 desktop UI."""
from __future__ import annotations
import argparse
from pathlib import Path
from .bse_client import BSEClient
from .resolver import resolve
from .library import build_library
from .errors import FilingForgeError
from .progress import ProgressEvent


def _bar(ev: ProgressEvent) -> None:
    print(f"[{ev.percent:3d}%] {ev.message}")


def main() -> int:
    ap = argparse.ArgumentParser(prog="python -m engine")
    ap.add_argument("company")
    ap.add_argument("dest", nargs="?", default="./FilingForgeLibrary")
    ap.add_argument("--years", type=int, default=5)
    args = ap.parse_args()
    client = BSEClient()
    try:
        candidates = resolve(args.company, client)
        chosen = next((c for c in candidates if c.is_primary), candidates[0])
        print(f"Using: {chosen.company} ({chosen.scrip_code})")
        # Maintainer CLI only. The Plan-04 UI passes the user-chosen ticker directly; this naive
        # name-based derivation would collide distinct companies (e.g. "Tata Consultancy" and
        # "Tata Motors" both → "TATA"), so we suffix the scrip code to keep folders unique.
        ticker = f"{chosen.company.split()[0].upper()}-{chosen.scrip_code}"
        res = build_library(chosen.scrip_code, ticker, Path(args.dest),
                            [], args.years, client, on_progress=_bar, everything=True)
        print(f"\nDone. {len(res.downloaded)} new, {len(res.skipped)} already had, "
              f"{len(res.failed)} skipped. Library: {Path(args.dest).resolve()}")
        return 0
    except FilingForgeError as e:
        print(f"\n{e.user_message}")
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
