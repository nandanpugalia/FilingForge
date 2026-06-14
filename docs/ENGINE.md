# FilingForge Engine

The FilingForge engine is the free, MIT-licensed Python core behind the desktop
app. It resolves BSE-listed companies, downloads official BSE filings, converts
text-based PDFs into clean Markdown, and keeps a local `INDEX.md`-first library.

It does not call any LLM, send telemetry, or upload user files. The only network
traffic is to public BSE endpoints while fetching filings.

## Install For Development

From the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[api,dev]"
```

On Windows, activate the virtual environment with:

```powershell
.venv\Scripts\activate
```

## Run The CLI

The maintainer CLI is useful for smoke tests and scripts:

```bash
python -m engine "TANLA" ./FilingForgeLibrary --years 5
```

That command:

1. Resolves the company name against BSE.
2. Chooses the BSE-preferred result.
3. Downloads filings from the last 5 years.
4. Writes PDFs, Markdown siblings, and indexes under `./FilingForgeLibrary`.

The desktop app is the main user experience, but the CLI is intentionally kept
small and real so the engine can be tested without Tauri.

## Use The Python API

```python
from pathlib import Path

from engine import BSEClient, CURATED, build_library, resolve


def progress(event):
    print(f"[{event.percent:3d}%] {event.message}")


client = BSEClient()
try:
    candidates = resolve("TANLA", client)
    chosen = next((c for c in candidates if c.is_primary), candidates[0])
    specs = [spec for spec in CURATED if spec.default_on]

    result = build_library(
        chosen.scrip_code,
        chosen.symbol or chosen.company.split()[0].upper(),
        Path("./FilingForgeLibrary"),
        specs,
        years=5,
        client=client,
        on_progress=progress,
    )

    print(result.downloaded, result.skipped, result.failed)
finally:
    client.close()
```

See [`examples/python_api.py`](../examples/python_api.py) for a runnable version.

## Category Specs

The engine models filing choices with `CategorySpec`. The default high-signal
set is:

| Key | Folder | BSE Category |
|---|---|---|
| `annual_report` | `annual-reports` | Annual reports |
| `results` | `quarterly` | Financial results |
| `investor_ppt` | `investor-ppts` | Investor presentations |
| `concall` | `concalls` | Earnings call transcripts |

Passing `everything=True` to `build_library` asks BSE for every available filing
in the selected time window. Passing a list of specs keeps the pull focused.

## Library Layout

A generated library is plain files on disk:

```text
FilingForgeLibrary/
  INDEX.md
  _filingforge/
    report_helper.md
  TANLA/
    INDEX.md
    annual-reports/
      2025-...pdf
      2025-...md
    quarterly/
      ...
```

Each company folder gets its own `INDEX.md`; the library root gets a master
`INDEX.md`. Point a coding agent or desktop AI at the library root first.

## Tests

Run the Python suite from the repository root:

```bash
pytest
```

The test suite uses mocked transports and fixtures by default, so it should not
depend on BSE being online. For a live smoke check, run the CLI against a small
destination folder and inspect the generated `INDEX.md`:

```bash
python -m engine "TANLA" /tmp/ff-smoke --years 1
```

Live smoke checks touch public BSE endpoints and should be used sparingly.

## Local-First Boundary

The engine boundary is deliberately strict:

- No LLM calls.
- No telemetry.
- No user accounts.
- No uploads.
- No paid or private data sources.
- Public BSE filings only.

If a change needs intelligence, keep it in a Skill prompt-pack or a separate
user-controlled workflow, not inside the engine.
