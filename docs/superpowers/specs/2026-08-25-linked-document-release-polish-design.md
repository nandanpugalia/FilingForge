# Linked-document release polish design

**Date:** 2026-08-25
**Status:** Approved in conversation
**Parent:** `2026-08-24-assisted-linked-document-import-design.md`

## Outcome

Prepare the linked-document recovery work for a v0.1.18 beta without making ordinary
FilingForge pulls heavier. The engine continues to do extra issuer-site work only after a
PDF in one of the four supported categories is positively identified as a cover letter.

Public stable promotion remains a separate, explicit decision after the beta installer has
passed the real upgrade and packaged-app gate.

## Progress language

Progress messages use FilingForge's own document vocabulary instead of verbatim BSE prose.
For supported categories, the visible label is the document type plus a period when one can
be derived safely, otherwise the filing date. Examples:

- `Downloading Investor presentation — quarter ended 31 Dec 2025…`
- `Downloading Annual report — FY 2025-26… — large file, this can take a moment`
- `Already in your library: Financial results — quarter ended 30 Jun 2026`

The formatter is local string processing. It performs no network or filesystem work.

## New filenames

Only newly saved files receive concise semantic names. The stable filing date and BSE
`news_id` remain in every filename, so sorting, uniqueness and provenance are preserved.
Existing files are neither renamed nor moved. An incremental refresh therefore keeps every
existing library byte-for-byte in place and applies the cleaner convention only to new files.

If a trustworthy period cannot be extracted, the category label and filing date are enough;
FilingForge must not guess a quarter or financial year.

## Completion screen: action-first option A

For a complete company library the screen leads with:

1. `Library ready`
2. company name
3. total official filings ready for the user's AI
4. primary button: `Copy AI instructions`
5. secondary button: `Open library`
6. compact new/already-present/failed summary and category breakdown

The raw absolute path is not displayed as a large UI block. It remains inside the copied
instructions because the AI needs the exact company `INDEX.md` path.

The copied text is:

```text
I've built a local filings library for <company>.
Read its index first: <root>/<ticker>/INDEX.md
Use only the official filings in that library and cite the filenames you rely on.
Tell me when you've read the index and are ready, then wait for my question.
```

FilingForge never copies automatically. Success changes the button briefly to `Copied`.
Failure shows an inline explanation and leaves the button available for retry.

## Truthful states

The result contract has four distinct facts:

- `ready`: complete persisted documents currently in the company library;
- `downloaded`: documents newly added by this run;
- `skipped`: documents already present and therefore not downloaded again;
- `failed`: attempted documents that could not be added.

`skipped` is never described as a missing attachment. A refresh with zero downloads may still
say the library is ready because `ready` describes the persisted library. A run with pending
source PDFs says `Library almost ready` and keeps the guided recovery actions visible; it does
not offer the finished-library AI handoff until the pending list is empty. A cancelled run says
the partial library was saved and reports only complete persisted documents.

## Release gates

### Local gate — no public mutation

- full Python, UI, Rust, lint and production UI build checks;
- deterministic first-build, refresh, no-cover and unresolved/import tests;
- real-browser interaction at 1440×900 and 390×844, with screenshots inspected;
- frozen sidecar and packaged macOS beta smoke;
- live KFin regression plus an ordinary no-cover company comparison;
- version metadata set to 0.1.18 and release tag/config mismatch prevented.

### Beta-channel gate — requires later approval to push

- push the reviewed branch and a `v0.1.18-betaN` tag;
- require both macOS and Windows release jobs to succeed;
- verify updater metadata and signatures;
- install the notarized/stapled beta on macOS;
- upgrade an existing v0.1.17 install through the opt-in beta channel;
- repeat the KFin and ordinary-company smoke in the shipped package.

### Stable gate — requires a final explicit approval

Promote the already-tested beta release to stable without rebuilding. Then verify
`releases/latest`, the stable updater feed and website downloads resolve to v0.1.18.

No GitHub issue reply is posted until this stable decision is made.

## Deferred

- Required private email plus deliberate anonymous report submission is a separate patch.
- Renaming old library files.
- Arbitrary crawling, browser automation or background folder watchers.
