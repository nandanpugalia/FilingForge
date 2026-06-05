# FilingForge UI

The React front-end for FilingForge — turns any Indian company's BSE filings into a
clean, AI-ready library. This app is a thin client over the FilingForge engine API.

## Prerequisites

- Node 26+
- The **v0.2 engine** running locally. The UI expects the v0.2 build, which provides
  everything-mode, the `/library` endpoint, and the BSE `symbol` field on `/resolve`
  candidates. An older engine will not satisfy these endpoints.

## Running locally

Start the engine API from the **repo root** (a separate terminal):

```bash
python -m api          # serves the FilingForge engine on http://127.0.0.1:8765
```

Then start the UI dev server (from `ui/`):

```bash
npm install            # first time only
npm run dev            # Vite dev server on http://localhost:5173
```

The UI talks to the engine at `http://127.0.0.1:8765` by default. Override with the
`VITE_API_BASE` env var if the engine runs elsewhere.

## Tests

```bash
npm run test           # unit + component tests (Vitest, jsdom)
npm run e2e            # end-to-end happy path (Playwright)
```

### Unit tests (`npm run test`)

Vitest runs the suite under `src/__tests__/`. The Vitest config excludes `e2e/**`.

### E2E (`npm run e2e`)

Playwright drives the full search → configure → build → done flow. The REST endpoints
are mocked via `page.route`, and a controllable fake `EventSource` is injected with
`addInitScript` to deterministically drive the SSE build-progress stream (council R10 —
routing live SSE through `page.route` is unreliable). No engine is required to run the
E2E test; it is fully self-contained.

Projects: `chromium` and `webkit` (the macOS WKWebView target the packaged app ships
on). First run, install the browsers:

```bash
npx playwright install chromium webkit
```

Playwright auto-starts the dev server (`npm run dev`) and reuses an existing one on
`:5173` if already running.
