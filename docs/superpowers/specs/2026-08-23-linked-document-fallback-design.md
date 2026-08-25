# Linked-document fallback design

**Date:** 2026-08-23  
**Status:** Approved for local feasibility testing; not approved for release  
**Issue:** GitHub #21 exposed BSE filings whose attachment is a cover letter rather than the promised document.

## Context

FilingForge currently accepts an attachment when it starts with the PDF magic bytes. That proves the file format, not that the PDF contains the annual report, concall transcript, investor presentation, or financial results named by BSE.

KFin Technologies demonstrates the failure. Its FY2024-25 and FY2025-26 BSE annual-report attachments are one- or two-page exchange letters that point to the company's annual-report page. The actual reports are separate 14.9 MB and 26.2 MB PDFs on the official investor site.

A bounded live audit found the same pattern outside annual reports:

- KFin Technologies: annual-report cover letters.
- Maruti Suzuki: concall-transcript cover letters.
- HDFC Bank: investor-presentation cover letters.

The audit covered 15 companies and 164 recent high-signal filings. It found seven confirmed link-only cover letters. The sample is evidence that the problem crosses categories, not a prevalence estimate.

## Goals

1. Never silently save a link-only cover letter as the requested substantive document.
2. Retrieve the real document automatically when an official linked source can be resolved unambiguously.
3. Preserve FilingForge's lightweight, local-first architecture and current UI, folder layout, deduplication, refresh, CLI, API, and MCP behaviour.
4. Fail honestly when the real document cannot be resolved.
5. Prove feasibility locally on at least 15 real cover-letter cases before changing the production path or preparing a release.

## Non-goals

- Crawling an entire company website.
- Searching Google, Bing, or third-party indexes.
- Running Playwright, Chromium, or JavaScript in the Python sidecar.
- Guaranteeing support for every investor-relations website.
- Adding a permanent adapter for a company without a reproduced real-world case.
- Changing arbitrary low-signal filing categories such as notices, ballots, or routine board filings.
- Shipping, tagging, deploying, or replying to GitHub issues during the local feasibility phase.
- Changing the in-app reporter or email flow in this sub-project. That improvement gets a separate design and implementation cycle.

## Considered approaches

### 1. KFin-only annual-report patch

Smallest immediate change, but it leaves the identical defect in concalls and presentations and creates no reusable boundary. Rejected as unsustainable.

### 2. Bounded linked-document fallback

Detect a cover letter semantically, follow its single official link, resolve one strongly matching document, and provide a small adapter seam for proven dynamic sites. This covers the observed pattern without turning FilingForge into a web crawler. **Selected.**

### 3. Universal headless-browser crawler

This could render arbitrary dynamic investor sites but would add a browser runtime, large dependencies, slower builds, new packaging risk, and a permanent website-automation maintenance burden. Rejected.

## Scope

The fallback applies only to the four substantive curated categories where a cover letter would poison the AI-ready library:

- Annual Reports (`annual-reports`)
- Concall Transcripts (`concalls`)
- Investor Presentations (`investor-ppts`)
- Financial Results (`quarterly`)

All other filing categories retain the current byte-validation path.

## Processing flow

1. List the filing from BSE exactly as today.
2. Download the BSE attachment exactly as today.
3. Verify `%PDF-` exactly as today.
4. For an in-scope category, run the bounded cover-letter detector.
5. If the PDF is substantive, return it unchanged.
6. If it is a cover letter, extract safe official HTTPS links from PDF annotations and text.
7. Resolve candidates from the linked source, using the generic resolver first and a registered adapter only when needed.
8. Rank candidates by filing type, financial period or quarter, and relevant date.
9. Continue only when there is one unique strong match.
10. Download the candidate, validate `%PDF-`, and run the cover-letter detector again.
11. Return the substantive replacement bytes under the original BSE filing identity.
12. If any step is ambiguous or unsupported, report the filing as failed; do not save the cover letter as the requested document.

## Cover-letter detector

File size is only a cheap pre-filter, never the decision. Genuine transcripts can be small.

A PDF is classified as a linked cover letter only when multiple independent signals agree:

- It belongs to one of the four in-scope categories.
- It is short enough to inspect cheaply.
- Its first pages contain exchange-letter structure or language, such as BSE/NSE addressees and a subject line.
- It states that the requested document was uploaded, is available, or can be accessed through a website or link.
- It contains at least one external HTTPS link.

The detector must reject size-only and page-count-only heuristics. A short substantive document remains valid.

## Link extraction and safety

Links come only from the official BSE attachment. FilingForge will:

- Accept HTTPS only.
- Reject credentials in URLs.
- Reject localhost, IP literals, and hosts resolving to loopback, private, link-local, multicast, or reserved addresses.
- Bound redirects, response size, and timeouts.
- Fetch at most one landing page and one replacement PDF per cover letter.
- Never execute page JavaScript.
- Never follow a second landing-page hop.
- Cache one landing-page result in memory for the duration of a build so several filings do not repeatedly fetch the same page.

## Candidate resolution

### Generic resolver

The generic resolver reads normal HTML links and direct PDF links. It records candidate URL plus nearby link text. It scores candidates using normalized evidence from the BSE filing and cover letter:

- Document-type terms: annual report, transcript, presentation, or financial results.
- Financial-year forms such as `2025-26`, `2025_26`, `FY26`, and `2026` where appropriate.
- Quarter forms such as `Q3FY26`, `Q3 FY 2025-26`, and equivalent punctuation variants.
- Call, quarter-end, or publication date when present.
- Negative terms for a clearly different document type or period.

Resolution requires one unique candidate above a fixed confidence threshold. Ties, weak matches, and missing period evidence fail instead of guessing.

### Adapter seam

Some sites render document lists from a public JSON endpoint and expose no useful PDF links in the initial HTML. A registered adapter may turn one known landing URL into the same normalized candidate list used by the generic resolver.

Adapters are:

- Selected by exact hostname, not company name.
- Small and isolated from matching and download logic.
- Backed by recorded fixtures and one guarded live smoke.
- Added only for a reproduced external case.

Maruti Suzuki is the initial dynamic-site case. Its public Adobe AEM persisted-query response contains document type, year range, date, description, and PDF path, so it can be supported without a browser.

## Identity, storage, and refresh

The real company-IR PDF retains the original BSE filing's `news_id`, date, headline, category, and destination folder. Existing incremental refresh therefore skips the resolved document on later runs exactly as it skips ordinary BSE attachments.

No new account, database, background service, or persistent web cache is introduced. The company-IR URL is provenance for the resolved bytes, not a second filing identity.

## Errors and user experience

The normal successful path remains visually unchanged.

When a cover letter cannot be resolved, the build records that filing as failed and emits a specific progress message that the linked document could not be found safely. Completed filings remain intact, the index is rebuilt from actual files, and partial success continues to work as today.

The system must not report success for a saved cover letter. It also must not remove a previously valid substantive document during a failed refresh.

## Local feasibility gate

Before product integration, create a local validation corpus with:

- At least 15 confirmed cover-letter filings.
- At least five companies.
- At least three of the four in-scope categories.
- A mix of direct-PDF, static-HTML, and dynamic-JSON landing sources where available.
- At least 30 substantive control PDFs, including small genuine transcripts and presentations.

Run an isolated prototype against recorded inputs and guarded live sources. The design proceeds to product integration only if all of the following hold:

1. Detection finds all 15 confirmed cover letters.
2. Detection produces zero false positives across the 30 substantive controls.
3. KFin annual reports, HDFC presentations, and Maruti transcripts resolve to substantive PDFs end to end.
4. At least 80% of the 15 cover letters resolve through the generic resolver or no more than two small host adapters.
5. Every unresolved or ambiguous case fails honestly; none saves the cover letter as the requested document.
6. Normal BSE downloads make no additional network request.
7. The added inspection cost is negligible beside PDF download and Markdown conversion.

If the resolver misses the 80% threshold or needs more than two host adapters for the 15-case corpus, stop. Do not integrate the fallback. Reassess whether honest detection-only handling is more sustainable than automatic resolution.

## Product integration tests after the gate

If the feasibility gate passes, implementation remains test-driven and adds:

- Detector unit tests for every positive signal combination and false-positive control.
- URL-safety tests, including private hosts and unsafe redirects.
- Candidate-scoring tests for years, quarters, dates, ambiguity, and negative document types.
- Generic HTML resolver fixtures.
- Adapter contract tests and Maruti fixture tests.
- Replacement-PDF revalidation tests.
- Library tests proving the original BSE identity remains the dedup key.
- Failure-path tests proving cover letters do not enter the library or index.
- Full engine, API, MCP, and UI regression suites.
- Guarded live local builds for KFin, HDFC Bank, and Maruti Suzuki.

## Release gate

This design authorizes local research and testing only. A release requires a separate review of the feasibility results, completed integration tests, real local builds, and normal macOS/Windows release QA. GitHub replies are revisited only after the local result is known.
