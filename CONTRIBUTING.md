# Contributing to FilingForge

Thanks for your interest. FilingForge is a small, local-first desktop app
maintained in the open, and contributions are welcome.

This guide covers how to get set up, how the project is shaped, and what makes a
change easy to merge.

## What FilingForge is (and the one boundary that matters)

FilingForge turns any Indian company's official **BSE** filings into a clean,
**AI-ready Markdown** library on your own machine: it downloads filings, converts
each PDF into a tidy `.md`, and builds per-company and master `INDEX.md` files.

Everything runs locally. **The engine never calls an LLM, and nothing leaves the
user's computer.** Please keep it that way — no network calls to AI providers, no
telemetry, no "just this once" exceptions. The intelligence lives in **Skills**:
prompt-packs the user runs in *their own* Claude or Codex against the library
FilingForge produced. Skills are plain Markdown prompt files, not code that calls
a model. If you're proposing a feature, it should respect this split.

## Project layout

- `ui/` — React + TypeScript front end (Tauri v2 shell; macOS + Windows).
- `engine/` — the Python conversion/indexing engine (BSE fetch, PDF → Markdown,
  index building). Pure logic, no model calls.
- `api/` — a thin **FastAPI** layer that exposes the engine over a local loopback
  service (`127.0.0.1:8765`). Shipped as a **PyInstaller**-bundled sidecar.
- `ui/src/skills/` — the Skill prompt-packs (e.g. Business Model Brief).

The Rust/Tauri shell launches the bundled Python sidecar and talks to it over
loopback. In dev you run the pieces yourself (below).

## Getting set up

You'll need Node 20, Python 3.11, and the Rust toolchain (for the Tauri shell).

```bash
git clone https://github.com/nandanpugalia/FilingForge
cd FilingForge

# Front end
cd ui
npm ci
cd ..

# Python engine + API (in a virtualenv)
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[api,dev]" pyinstaller   # api=FastAPI/uvicorn, dev=pytest; pyinstaller builds the sidecar
```

## Running the tests

```bash
# Python engine + API
pytest                              # from repo root, with .venv active

# UI
cd ui && npm test                   # vitest
```

Please run both before opening a PR. New behavior should come with tests; bug
fixes ideally come with a test that would have caught the bug.

## Dev flow

For day-to-day work you generally want the engine API running and the UI in dev
mode:

```bash
# Terminal 1 — engine API on loopback (serves 127.0.0.1:8765)
source .venv/bin/activate
python -m api

# Terminal 2 — UI
cd ui && npm run dev
```

(If a script name differs from your checkout, check `ui/package.json` and
`api/` for the current entry points — they're the source of truth.)

## Coding norms

- **Match the surrounding style.** This codebase favors small, readable functions
  over cleverness. When in doubt, mirror the file you're editing.
- **Keep the LLM-free boundary.** The engine and API must not call any model or
  phone home. Intelligence belongs in Skills.
- **Tests for new behavior.** vitest for the UI, pytest for Python.
- **Type things.** TypeScript on the UI side; type hints on new Python.
- **Keep changes scoped.** One logical change per PR. Avoid drive-by reformatting
  that buries the real diff.

## Proposing changes

- **Small fixes** (typos, clear bugs, docs): just open a PR.
- **Anything larger** (new feature, dependency, behavior change, a new Skill):
  please open an issue first so we can agree on the shape before you build it.
  This saves everyone from a "great work, but this isn't the direction" review.

## Commit and PR etiquette

- Write clear commit messages — a short imperative subject (e.g.
  `fix: handle empty BSE result page`), and a body if the *why* isn't obvious.
- Reference the issue you're closing (`Closes #123`).
- Keep PRs focused and the diff readable. Fill in the PR template checklist.
- Be patient and kind in review — this is an indie project maintained in spare
  time, and so is your reviewer's attention.

By contributing, you agree your contributions are licensed under the project's
[MIT License](LICENSE).
