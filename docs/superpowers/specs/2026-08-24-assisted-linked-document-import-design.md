# Assisted linked-document import design

**Date:** 2026-08-24
**Status:** Approved in conversation; awaiting written-spec review
**Parent design:** `2026-08-23-linked-document-fallback-design.md`

This amendment supersedes the parent design's unresolved-item user experience and its 80%
automatic-resolution integration gate. The detector, resolver safety boundaries, category scope,
and release restrictions remain unchanged.

## Decision

When BSE supplies a cover letter instead of an annual report, concall transcript,
investor presentation, or financial result, FilingForge first attempts the bounded,
deterministic resolver from the parent design. If the real PDF cannot be selected safely,
FilingForge creates a pending document slot and guides the user through obtaining the PDF.

The user supplies only the source file. FilingForge remains responsible for the destination
folder, filename, PDF validation, Markdown conversion, deduplication, and index update.
An unresolved cover letter is never saved or counted as the requested document.

## Why this replaces an all-automatic release gate

The local feasibility audit found 33 confirmed cover letters across five issuers and three
substantive categories. Detection found 33/33 with zero false positives across 30 substantive
controls, while deterministic resolution recovered 18/33. That is strong enough to prevent
library contamination but not strong enough to promise universal automatic recovery.

The production success criterion is therefore:

- zero wrong documents;
- zero cover letters masquerading as substantive documents;
- automatic retrieval whenever the result is unambiguous; and
- an actionable, library-preserving completion path for every unresolved filing.

## User flow

1. A normal build continues unchanged for substantive BSE PDFs.
2. For a detected cover letter, FilingForge attempts deterministic retrieval.
3. If retrieval succeeds, FilingForge saves and converts the real PDF normally.
4. If retrieval is unsafe or unsupported, the build completes with a pending document slot.
5. The result says **“12 documents ready · 3 awaiting source PDFs”** and offers
   **“Complete remaining documents.”**
6. Each pending item shows its document type and period plus one of:
   - **Get document** — opens the safe official issuer document or landing page extracted from
     the BSE notice.
   - **View BSE notice** — used when no safe issuer URL can be extracted.
7. After downloading the PDF, the user clicks **Use downloaded PDF**. A native file picker opens
   in the system Downloads folder when available and accepts one PDF.
8. FilingForge validates and imports the selected PDF into the pending slot, then updates the
   screen to **Ready**.

The first release uses explicit file selection. Automatic Downloads-folder watching and
drag-and-drop are deferred; neither is required for a complete library outcome.

## Pending document identity

Pending slots are stored locally per company and keyed by the original BSE `news_id`. Each slot
retains the original filing date, headline, category, destination folder, expected document type
and period, BSE attachment URL, and a safe issuer URL when available.

A pending slot is not added to the seen ledger. A later refresh may therefore retry automatic
resolution. The pending record is replaced, not duplicated, when the same `news_id` is seen again.

After a successful assisted import, FilingForge uses the original BSE filing identity for naming,
provenance, and deduplication, records the `news_id` as seen, and removes the pending slot.

## Import transaction

The engine, not the UI, performs the import:

1. Resolve the selected path and require a regular `.pdf` file.
2. Read it with bounded size handling and verify PDF magic bytes.
3. Confirm it is parseable and is not another detected cover letter.
4. Copy it atomically into the existing company/category/year layout. Do not move or delete the
   user's original download.
5. Generate the Markdown sibling using the original BSE filing metadata.
6. Record the filing as seen only after both PDF and Markdown exist.
7. Remove the pending record and rebuild company and master indexes.

If validation or conversion fails, no final library file or seen-ledger entry is left behind. The
slot remains pending with a friendly explanation so the user can select a different PDF.

## Link safety and presentation

Only HTTPS issuer URLs extracted from the BSE attachment, or their already-validated redirect
targets, may be shown. The destination hostname is visible in the UI. FilingForge does not invent
links from web searches.

An issuer landing page is labelled **Get document**, not presented as though it were the PDF.
When no safe issuer URL exists, FilingForge retains the BSE notice URL and clearly explains that
the full document link could not be read.

## Scope and lightweight behaviour

This path applies only to annual reports, concalls, investor presentations, and financial results.
The cover-letter detector runs locally after an already-required download. The resolver performs
additional network work only for detector-positive filings. Normal filings gain no extra request,
browser process, background service, or filesystem watcher.

## Test requirements

Implementation remains test-driven and must prove:

- unresolved cover letters create or update one pending slot and never enter the library index;
- build results distinguish ready documents from pending source PDFs;
- safe issuer URLs and BSE-notice-only fallbacks produce the correct actions;
- selecting a valid PDF creates the correctly named PDF and Markdown in the expected folder;
- the imported document retains the original BSE identity and is skipped on refresh;
- the source file in Downloads remains untouched;
- invalid, unreadable, oversized, or cover-letter PDFs leave the slot pending and the library clean;
- an interrupted import leaves no partial final file;
- company and master indexes update only after a complete import; and
- normal BSE filings still make no additional network request.

UI work must also pass the existing real-browser verification requirement on desktop and mobile
viewport sizes before any release claim.

## Deferred work

- Watching Downloads for a newly created PDF and offering one-click confirmation.
- Drag-and-drop onto a pending slot.
- Headless-browser automation of arbitrary investor-relations websites.
- Search-engine discovery of missing documents.
- Shipping, release tagging, deployment, and GitHub issue replies.
