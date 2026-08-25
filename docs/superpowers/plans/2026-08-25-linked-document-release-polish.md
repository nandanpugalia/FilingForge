# Linked-Document Release Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the linked-document recovery beta concise, truthful, regression-safe and ready for a separately approved v0.1.18 beta release.

**Architecture:** Add one pure document-presentation formatter in the engine and reuse it for progress and new filenames without touching existing files. Keep the API result contract explicit, render the completion screen from those facts, and protect the release pipeline with a tag/version check. Preserve the detector's lazy network boundary.

**Tech Stack:** Python 3.11, pytest, React 19, TypeScript, Vitest, Playwright, ESLint, Tauri 2, Rust, GitHub Actions.

---

### Task 1: Lock semantic progress labels and filenames

**Files:**
- Modify: `engine/organiser.py`
- Modify: `engine/library.py`
- Test: `engine/tests/test_organiser.py`
- Test: `engine/tests/test_library.py`

- [ ] **Step 1: Write the failing filename tests**

Add assertions that a supported filing whose headline begins `Please find attached` receives a
new filename containing the semantic category label and period, not that boilerplate; assert a
filing with no trustworthy period falls back to category plus filing date; assert the sanitized
`news_id` suffix still makes same-date filings unique.

- [ ] **Step 2: Verify RED**

Run:

```bash
.venv/bin/python -m pytest engine/tests/test_organiser.py -q
```

Expected: the new semantic-name assertions fail against `_safe_name()`.

- [ ] **Step 3: Implement the pure formatter and reuse it**

Add pure helpers returning a display label and semantic filename stem from `Filing`. Recognize
only the four supported folder names and explicit FY/Q/quarter-ended expressions. Preserve the
existing date prefix and `__<news_id>` uniqueness suffix. Leave unknown categories on the current
sanitized-headline path.

- [ ] **Step 4: Write and verify failing progress-copy tests**

Capture `ProgressEvent`s for an ordinary build and refresh. Require `Downloading <semantic label>`
and `Already in your library: <semantic label>`, and reject `Downloading Please find attached`.

- [ ] **Step 5: Make progress use the same formatter and verify GREEN**

Run:

```bash
.venv/bin/python -m pytest engine/tests/test_organiser.py engine/tests/test_library.py engine/tests/test_linked_document_integration.py -q
```

Expected: PASS, including the existing zero-issuer-request control.

### Task 2: Make result facts and completion copy truthful

**Files:**
- Modify: `ui/src/components/DoneView.tsx`
- Modify: `ui/src/flow.ts`
- Modify: `ui/src/types.ts`
- Test: `ui/src/__tests__/views.test.tsx`
- Test: `ui/src/__tests__/flow.test.ts`

- [ ] **Step 1: Replace the old expectations with failing truthfulness tests**

Require these independent cases:

```text
ready=28, downloaded=28, skipped=0  -> 28 official filings ready; 28 added
ready=28, downloaded=0, skipped=28  -> 28 official filings ready; 28 already in library
ready=28, downloaded=2, skipped=26  -> 28 official filings ready; 2 new; 26 already in library
ready=12, pending=3                 -> Library almost ready; 3 need source PDFs; no AI handoff
cancelled=true, ready=7             -> Saved safely; 7 complete filings ready
```

Explicitly assert the phrase `had no attached PDF` is absent.

- [ ] **Step 2: Verify RED**

Run:

```bash
cd ui && npm test -- src/__tests__/views.test.tsx src/__tests__/flow.test.ts
```

Expected: current completion copy and action order fail.

- [ ] **Step 3: Implement action-first option A**

Render `Library ready`, the company, total-ready hero number, primary `Copy AI instructions`,
secondary `Open library`, compact run facts and the existing breakdown. Preserve guided pending
cards and hide the finished-library AI action while pending.

- [ ] **Step 4: Verify GREEN**

Run the focused tests again and require PASS.

### Task 3: Make AI handoff reliable

**Files:**
- Modify: `ui/src/components/DoneView.tsx`
- Test: `ui/src/__tests__/views.test.tsx`

- [ ] **Step 1: Write failing clipboard and prompt tests**

Require the exact company-index-only instructions from the approved design, absence of the master
`Other companies` path, no clipboard call on render, `Copied` after success, and an inline retryable
error after rejection or an unavailable Clipboard API.

- [ ] **Step 2: Verify RED**

Run the focused view test and confirm the old prompt/error behavior fails.

- [ ] **Step 3: Implement the minimal three-state copy action**

Use `idle | copied | error`; call the Clipboard API only on click, clear stale errors before retry,
and keep the library path out of the visible layout while retaining it in copied text.

- [ ] **Step 4: Verify GREEN**

Run the focused test and require PASS.

### Task 4: Make the standard quality gate clean

**Files:**
- Modify: `ui/eslint.config.js`
- Modify as required by real lint findings: `ui/src/components/ReadyGate.tsx`, `ui/src/components/SearchField.tsx`, `ui/src/components/SkillsOverlay.tsx`, `ui/src/lib/useUpdate.ts`, `ui/src/__tests__/sse.test.ts`
- Test: existing Vitest suites

- [ ] **Step 1: Prove generated artifacts are the first lint failure source**

Run `cd ui && npm run lint` and retain the baseline: generated `src-tauri/target/**` files plus
the enumerated source violations.

- [ ] **Step 2: Exclude only generated/build directories**

Extend `globalIgnores` to `dist`, `node_modules`, `src-tauri/target`, and Playwright output. Do not
ignore `src`, test files, or disable ESLint globally.

- [ ] **Step 3: Resolve source violations without changing user-visible behavior**

Replace explicit test `any` types; keep component-only exports in component modules; defer effect
callbacks where React requires external synchronization; move impure timestamps to event handlers
or refs. Add focused regression tests before any behavior-affecting refactor.

- [ ] **Step 4: Verify quality and behavior**

Run:

```bash
cd ui && npm run lint && npm test -- --run && npm run build
```

Expected: all commands exit 0.

### Task 5: Guard v0.1.18 release metadata

**Files:**
- Modify: `ui/src-tauri/tauri.conf.json`
- Modify: `ui/src-tauri/Cargo.toml`
- Modify mechanically: `ui/src-tauri/Cargo.lock`
- Create: `scripts/check_release_version.py`
- Create: `scripts/test_check_release_version.py`
- Modify: `.github/workflows/release.yml`
- Modify: `.github/workflows/ci.yml`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Write failing release-version tests**

Test accepted tags `v0.1.18` and `v0.1.18-beta1`, rejection of `v0.1.17-beta1`, malformed tags,
and mismatch between Tauri and Cargo package versions.

- [ ] **Step 2: Verify RED**

Run:

```bash
.venv/bin/python scripts/test_check_release_version.py
```

Expected: failure because the checker does not exist.

- [ ] **Step 3: Implement the checker and align metadata**

Set both manifests to `0.1.18`, update the lockfile through Cargo, add an unreleased v0.1.18
changelog entry, and run the checker in CI and before the release build. A beta suffix belongs to
the Git tag, not the application version.

- [ ] **Step 4: Verify GREEN**

Run the checker tests, `cargo test`, and the checker against `v0.1.18-beta1`.

### Task 6: Browser and packaged local gate

**Files:**
- Modify: `ui/e2e/happy.spec.ts`
- Modify: `ui/e2e/pending.spec.ts`
- Add screenshots under ignored `output/playwright/`

- [ ] **Step 1: Update browser assertions for action-first completion**

Cover first build, refresh, clipboard success/failure and pending import. Run Chromium and WebKit.

- [ ] **Step 2: Serve over HTTP and interact at both required viewports**

Run Playwright at 1440×900 and 390×844, inspect the images, and check console errors.

- [ ] **Step 3: Build the frozen sidecar and local v0.1.18 package**

Use the existing sidecar builder and Tauri bundle. Validate `/health`, ordinary build, pending import,
restart persistence and clean process exit.

- [ ] **Step 4: Run live regression comparisons**

Build KFin in a fresh temporary library and confirm the PDFs, Markdown siblings, seen ledger and index
agree. Build one ordinary no-cover company and compare request behavior and completion counts. Existing
library refresh must add no duplicates and rename no old files.

- [ ] **Step 5: Produce the local gate report and stop**

Report commands, counts, screenshots, package hashes, observed timings and any residual risks. Do not
push, tag, publish, promote, deploy or reply to issues.

### Task 7: Separately approved beta and stable gates

**Files:** no implementation files unless the shipped-package gate reveals a defect.

- [ ] **Step 1: After explicit approval, push branch and beta tag**

Push `codex/linked-document-feasibility`, create `v0.1.18-beta1`, and wait for Mac + Windows artifacts,
updater JSON, signing and notarization/stapling.

- [ ] **Step 2: Test the real upgrade**

Opt a v0.1.17 install into beta, update in-app, verify v0.1.18 launches with the existing library intact,
and repeat ordinary/KFin/manual-import flows.

- [ ] **Step 3: Stop for final stable approval**

Only after explicit approval, promote the already-tested beta to stable and verify all stable endpoints.
