# Assisted Linked-Document Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect link-only BSE cover letters in the four substantive categories, retrieve the real issuer PDF when deterministic, and otherwise let the user select the downloaded PDF so FilingForge files, converts, deduplicates, and indexes it automatically.

**Architecture:** Promote the already-audited detector and bounded resolver from `spike/linked_document/` into a focused `engine/linked_documents/` package. The library orchestrator stores unresolved items in a versioned per-company pending ledger keyed by the original BSE `news_id`; a narrow FastAPI endpoint imports one selected local PDF transactionally. The React completion screen displays pending slots, opens only engine-validated official links, and uses the existing Tauri dialog foundation to select a PDF from Downloads.

**Tech Stack:** Python 3.11, pypdf, httpx, FastAPI/Pydantic, React 19, TypeScript, Tauri v2 dialog/path/shell APIs, pytest, Vitest, Playwright.

---

## Scope and file map

- Create `engine/linked_documents/` from the proven prototype: PDF evidence, URL safety, candidate matching, adapters, and resolution orchestration.
- Create `engine/pending.py`: versioned pending-slot persistence and transactional assisted import.
- Modify `engine/models.py`, `engine/fetcher.py`, and `engine/library.py`: carry pending results and invoke linked-document handling only for detector-positive scoped filings.
- Add `engine/tests/test_linked_document_integration.py` and `engine/tests/test_pending.py` plus promoted resolver tests/fixtures.
- Modify `api/schemas.py`, `api/routes.py`, and `api/jobs.py`: return pending slots and expose list/import operations.
- Add API route and build-flow tests.
- Create `ui/src/lib/pickPdfFile.ts` and `ui/src/components/PendingDocuments.tsx`.
- Modify `ui/src/types.ts`, `ui/src/api.ts`, `ui/src/App.tsx`, `ui/src/components/DoneView.tsx`, and `ui/src/theme.css`.
- Add Vitest and Playwright coverage for the guided completion flow.

Out of scope: arbitrary web crawling, browser automation in the sidecar, Downloads-folder watching, drag-and-drop, publishing a GitHub release, changing update feeds, deploying, and replying to GitHub issues.

### Task 1: Promote the audited detector and resolver behind a production boundary

**Files:**

- Create: `engine/linked_documents/__init__.py`
- Create: `engine/linked_documents/models.py`
- Create: `engine/linked_documents/evidence.py`
- Create: `engine/linked_documents/safety.py`
- Create: `engine/linked_documents/candidates.py`
- Create: `engine/linked_documents/adapters.py`
- Create: `engine/linked_documents/resolver.py`
- Create: `engine/tests/linked_documents/`
- Test: `engine/tests/linked_documents/test_*.py`

- [ ] **Step 1: Copy the proven prototype tests into the production test namespace and change imports only**

Move the 67 unit tests and the small Maruti fixture from `spike/linked_document/tests/` to
`engine/tests/linked_documents/`. Change imports from `spike.linked_document` to
`engine.linked_documents`. Do not weaken assertions or remove the live-audit artifacts from
`spike/`.

- [ ] **Step 2: Run the promoted tests and verify RED**

```bash
.venv/bin/python -m pytest engine/tests/linked_documents -q
```

Expected: collection fails because `engine.linked_documents` does not exist.

- [ ] **Step 3: Promote the implementation with production names and provenance**

Copy the focused prototype modules into `engine/linked_documents/`, then extend the result contract
so unresolved outcomes retain the validated action URL when one exists:

```python
@dataclass(frozen=True)
class Resolution:
    status: Literal["substantive", "resolved", "unresolved"]
    reason: str
    source_url: str | None = None
    action_url: str | None = None
    pdf: bytes | None = None
```

`action_url` is the validated direct PDF or landing URL extracted from the BSE attachment. It is
never search-derived. Update the production user agent to `FilingForge/0.1 linked-document`.

- [ ] **Step 4: Add failing tests for unresolved action provenance**

Add cases proving that an ambiguous static page returns its safe landing URL, while a cover letter
with no readable external link returns `action_url=None`. Also prove a substantive original makes
zero calls to the injected `fetch` function.

- [ ] **Step 5: Make the provenance tests pass and run the full promoted suite**

```bash
.venv/bin/python -m pytest engine/tests/linked_documents -q
```

Expected: all promoted tests and new provenance tests pass.

- [ ] **Step 6: Commit**

```bash
git add engine/linked_documents engine/tests/linked_documents
git commit -m "feat(engine): promote linked document detector and resolver"
```

### Task 2: Persist unresolved slots and import a selected PDF transactionally

**Files:**

- Create: `engine/pending.py`
- Modify: `engine/models.py`
- Modify: `engine/organiser.py`
- Test: `engine/tests/test_pending.py`

- [ ] **Step 1: Write failing pending-ledger tests**

Define tests around a frozen `PendingDocument` with these fields:

```python
@dataclass(frozen=True)
class PendingDocument:
    news_id: str
    date: str
    headline: str
    folder: str
    category: str
    expected_type: str
    expected_period: str | None
    bse_url: str
    issuer_url: str | None
    reason: str
```

The module exposes `list_pending(company: Path) -> list[PendingDocument]`,
`upsert_pending(company: Path, item: PendingDocument) -> None`,
`remove_pending(company: Path, news_id: str) -> None`, and
`import_pending_pdf(company: Path, news_id: str, source: Path) -> Path`.

Tests must prove JSON version 1 round-trips, repeated `news_id` replaces instead of duplicates,
unknown IDs fail clearly, unsafe ticker/news IDs cannot escape the company directory, and an empty
ledger is removed.

- [ ] **Step 2: Run focused tests and verify RED**

```bash
.venv/bin/python -m pytest engine/tests/test_pending.py -q
```

Expected: import failure because `engine.pending` does not exist.

- [ ] **Step 3: Implement the versioned ledger**

Use `<company>/.filingforge_pending.json` with this top-level shape:

```json
{"version": 1, "items": [{"news_id": "bse-news-123", "date": "2026-07-28", "headline": "Annual Report FY 2025-26"}]}
```

Write updates atomically through a sibling `.part`. Treat missing/corrupt/unknown-version ledgers
as empty for listing, but never overwrite a corrupt file during a read-only operation.

- [ ] **Step 4: Write failing import-transaction tests**

Test a valid source PDF, non-PDF bytes, unreadable PDF, another detected cover letter, an oversized
source, conversion failure, and an interrupted atomic write. The valid case must prove:

- the original source remains byte-for-byte unchanged;
- the destination uses the pending filing's category/year/name and original `news_id`;
- a Markdown sibling is produced with the original BSE provenance;
- the seen ledger is updated only after both final files exist;
- pending is removed and both indexes are rebuilt.

- [ ] **Step 5: Implement minimal transactional import**

Reconstruct an `engine.models.Filing` from the pending slot, cap input at the resolver's 100 MiB
PDF limit, validate `%PDF-`, parse it, reject another linked cover letter, atomically copy bytes
with `save_filing`, convert with `pdf_to_markdown`, record seen, remove pending, then rebuild company
and master indexes. On any error before completion, remove only this transaction's partial/final
outputs and keep the pending slot.

- [ ] **Step 6: Run tests and commit**

```bash
.venv/bin/python -m pytest engine/tests/test_pending.py engine/tests/test_organiser.py engine/tests/test_converter.py engine/tests/test_indexer.py -q
git add engine/pending.py engine/models.py engine/organiser.py engine/tests/test_pending.py
git commit -m "feat(engine): add transactional pending document import"
```

Expected: PASS.

### Task 3: Integrate detection, deterministic recovery, and pending results into builds

**Files:**

- Modify: `engine/fetcher.py`
- Modify: `engine/library.py`
- Modify: `engine/models.py`
- Test: `engine/tests/test_linked_document_integration.py`
- Test: `engine/tests/test_library.py`

- [ ] **Step 1: Write failing library integration tests**

Using injected BSE bytes and an injected issuer fetcher, prove four paths:

1. substantive BSE PDF: saved normally and issuer fetcher is never called;
2. cover letter + unique replacement: replacement PDF and Markdown are saved under original identity;
3. unresolved cover + safe issuer page: no PDF/Markdown is saved and one pending slot is returned;
4. unresolved cover without link: pending slot contains the BSE notice URL and `issuer_url=None`.

Also prove one unresolved item does not fail or cancel other filings.

- [ ] **Step 2: Run the focused tests and verify RED**

```bash
.venv/bin/python -m pytest engine/tests/test_linked_document_integration.py -q
```

Expected: failures because `LibraryResult` has no pending list and `_process` does not inspect PDFs.

- [ ] **Step 3: Add the production orchestration seam**

Extend `LibraryResult`:

```python
@dataclass
class LibraryResult:
    downloaded: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    pending: list[PendingDocument] = field(default_factory=list)
    cancelled: bool = False
```

Add `filing_attachment_url(filing) -> str` in `fetcher.py` so both ordinary BSE attachments and
annual-report archive URLs have explicit provenance. In `library._process`, inspect only the four
supported folders. Lazily construct one `httpx.Client` for the build only after a cover letter is
detected, use `fetch_public_document` for bounded issuer reads, and close it in `finally`.

For unresolved covers, call `upsert_pending`, append the slot to `result.pending`, emit a friendly
progress message, and continue. Do not call `record_seen`. For resolved covers, save replacement
bytes and retain the original filing identity.

- [ ] **Step 4: Pass focused and full engine tests**

```bash
.venv/bin/python -m pytest engine/tests/test_linked_document_integration.py engine/tests/test_library.py -q
.venv/bin/python -m pytest engine/tests -q
```

Expected: PASS; the normal-substantive test records zero issuer requests.

- [ ] **Step 5: Commit**

```bash
git add engine/fetcher.py engine/library.py engine/models.py engine/tests
git commit -m "feat(engine): route cover letters to recovery or pending import"
```

### Task 4: Expose pending slots and assisted import through the local API

**Files:**

- Modify: `api/schemas.py`
- Modify: `api/routes.py`
- Modify: `api/jobs.py`
- Modify: `api/tests/test_build_flow.py`
- Create: `api/tests/test_pending.py`

- [ ] **Step 1: Write failing response and route tests**

Require build results to return `pending` as serialized items, and add:

```text
GET  /pending?root=<library>&ticker=<ticker>
POST /pending/import
```

The import request is:

```json
{"root":"/library","ticker":"KFINTECH","news_id":"abc","path":"/Users/me/Downloads/report.pdf"}
```

Tests must cover successful list/import, missing company, unknown pending ID, invalid PDF, path
expansion, and a ticker that sanitizes differently from the requested value.

- [ ] **Step 2: Verify RED**

```bash
.venv/bin/python -m pytest api/tests/test_pending.py api/tests/test_build_flow.py -q
```

Expected: 404/validation failures because routes and schemas do not exist.

- [ ] **Step 3: Implement thin schemas and routes**

Add `PendingDocumentOut`, `PendingImportRequest`, and `PendingImportOut`. Routes resolve the company
only through `engine.organiser.company_dir(Path(root).expanduser(), ticker)` and delegate all file
validation/mutation to `engine.pending`. Return friendly `user_message` errors through the existing
error handler; never expose a traceback or arbitrary file contents.

`api.jobs.run_build` returns:

```python
{
    "downloaded": len(res.downloaded),
    "skipped": len(res.skipped),
    "failed": len(res.failed),
    "pending": [asdict(item) for item in res.pending],
    "cancelled": res.cancelled,
}
```

- [ ] **Step 4: Run API and full Python suites, then commit**

```bash
.venv/bin/python -m pytest api/tests/test_pending.py api/tests/test_build_flow.py -q
.venv/bin/python -m pytest -q
git add api engine
git commit -m "feat(api): expose pending document completion"
```

Expected: all Python tests pass.

### Task 5: Add the native PDF picker and typed UI API

**Files:**

- Create: `ui/src/lib/pickPdfFile.ts`
- Modify: `ui/src/types.ts`
- Modify: `ui/src/api.ts`
- Test: `ui/src/__tests__/api.test.ts`
- Create: `ui/src/__tests__/pickPdfFile.test.ts`

- [ ] **Step 1: Write failing type/API/picker tests**

Add this UI contract:

```ts
export interface PendingDocument {
  news_id: string;
  date: string;
  headline: string;
  folder: string;
  category: string;
  expected_type: string;
  expected_period: string | null;
  bse_url: string;
  issuer_url: string | null;
  reason: string;
}

export interface BuildResult {
  downloaded: number;
  skipped: number;
  failed: number;
  pending: PendingDocument[];
  cancelled?: boolean;
}
```

Test `importPendingPdf(root, ticker, newsId, path)` request/response mapping. Test that
`pickPdfFile()` dynamically calls `downloadDir()` and opens a single-file dialog filtered to
`pdf`, while plain-web mode returns `null`.

- [ ] **Step 2: Verify RED**

```bash
npm test --prefix ui -- --run src/__tests__/api.test.ts src/__tests__/pickPdfFile.test.ts
```

Expected: missing type/functions.

- [ ] **Step 3: Implement the typed client and picker**

Use dynamic imports of `@tauri-apps/api/path` and `@tauri-apps/plugin-dialog`; if resolving
Downloads fails, omit `defaultPath` and still open the picker. Cancellation returns `null` and is
not an error.

- [ ] **Step 4: Pass tests and commit**

```bash
npm test --prefix ui -- --run src/__tests__/api.test.ts src/__tests__/pickPdfFile.test.ts
git add ui/src
git commit -m "feat(ui): add guided PDF import client"
```

### Task 6: Build the pending-document completion screen

**Files:**

- Create: `ui/src/components/PendingDocuments.tsx`
- Modify: `ui/src/components/DoneView.tsx`
- Modify: `ui/src/App.tsx`
- Modify: `ui/src/theme.css`
- Modify: `ui/src/__tests__/views.test.tsx`
- Modify: `ui/src/__tests__/app.test.tsx`

- [ ] **Step 1: Write failing component tests**

Require these visible states and interactions:

- heading: `12 documents ready · 3 awaiting source PDFs`;
- one card per pending document with type, period/headline, reason, and visible hostname;
- `Get document` when `issuer_url` exists, otherwise `View BSE notice`;
- `Use downloaded PDF` invokes the picker and then the import API for that exact `news_id`;
- successful import removes only that card and increments the ready count;
- cancelled selection changes nothing;
- invalid import shows an inline friendly error and leaves the card pending;
- final imported card set yields the normal fully-ready completion screen.

- [ ] **Step 2: Verify RED**

```bash
npm test --prefix ui -- --run src/__tests__/views.test.tsx src/__tests__/app.test.tsx
```

Expected: missing pending UI and actions.

- [ ] **Step 3: Implement the minimal guided flow**

`App` owns the asynchronous action because it coordinates picker/API/library refresh. `DoneView`
remains presentational and delegates each pending action. Use `openExternal` for the engine-provided
URL. Disable only the card currently importing, label it `Adding and converting…`, and keep other
cards usable.

Do not call the library ready when `pending.length > 0`. Use:

```text
<ready> documents ready · <pending> awaiting source PDFs
```

The explanatory copy must say that FilingForge will place, convert, and index the selected PDF.

- [ ] **Step 4: Add focused styles without changing the overall visual language**

Use existing surface, border, font, button, focus, and error tokens. Cards must wrap URLs and remain
usable at 390 px width. Do not add a modal or a new navigation phase.

- [ ] **Step 5: Run UI tests, build, and lint**

```bash
npm test --prefix ui
npm run build --prefix ui
npm run lint --prefix ui
```

Expected: PASS with no TypeScript or lint errors.

- [ ] **Step 6: Commit**

```bash
git add ui/src
git commit -m "feat(ui): guide completion of linked documents"
```

### Task 7: Prove the end-to-end flow and produce a local beta artifact

**Files:**

- Modify: `ui/e2e/happy.spec.ts`
- Modify only if required by packaging discovery: `sidecar/filingforge-api.spec`
- Do not modify: `ui/src-tauri/tauri.conf.json` version, release workflow, update feeds, or tags.

- [ ] **Step 1: Add an end-to-end browser fixture for pending completion**

Mock one completed document and one pending item. Exercise opening the source action, selecting a
fixture PDF through an injected picker seam, completing import, and reaching fully-ready state.
Verify there are no console errors.

- [ ] **Step 2: Run full automated verification**

```bash
.venv/bin/python -m pytest -q
npm test --prefix ui
npm run build --prefix ui
npm run lint --prefix ui
npm run e2e --prefix ui
cargo test --manifest-path ui/src-tauri/Cargo.toml
```

Expected: every command passes. Record exact counts.

- [ ] **Step 3: Run guarded live document checks**

Run the existing linked-document fixtures and guarded live checks for KFin, HDFC Bank, and Maruti.
Confirm: at least one deterministic replacement saves a substantive PDF/Markdown pair; at least one
unsupported case creates a pending slot with a safe action; a normal substantive control makes no
issuer request; and assisted import completes the pending slot without changing the Downloads copy.

- [ ] **Step 4: Verify the real UI in a browser**

Serve the UI over HTTP, navigate through the pending completion flow, inspect the console, interact
with both source and import actions, and capture 1440×900 plus 390×844 screenshots. Open and inspect
both PNGs before judging the UI.

- [ ] **Step 5: Build the sidecar and local unsigned beta package**

```bash
.venv/bin/python sidecar/build_sidecar.py
npm run tauri build --prefix ui
```

Expected: a local installer under `ui/src-tauri/target/release/bundle/`. This is a test artifact,
not a GitHub beta release; do not tag, publish, notarize, deploy, or alter any update feed.

- [ ] **Step 6: Install and smoke-test the local beta**

Launch the packaged app, confirm the sidecar becomes ready, build a small normal library, exercise
one pending import using a disposable destination, reopen the app, and confirm the pending/completed
state persists correctly. Record the artifact path and observed results.

- [ ] **Step 7: Final regression and commit**

```bash
git diff --check
git status --short
git add ui/e2e docs/superpowers/plans/2026-08-24-assisted-linked-document-import.md
git commit -m "test: verify assisted linked document beta flow"
```

Stop for review with the local artifact path, test counts, live-case outcomes, screenshots, known
limitations, and confirmation that nothing was published.
