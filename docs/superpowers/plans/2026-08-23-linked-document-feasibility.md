# Linked-Document Fallback Feasibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove, with a local 15-cover-letter corpus and at least 30 substantive controls, whether FilingForge can safely detect and resolve link-only BSE cover letters without adding browser automation, broad crawling, or work to the normal download path.

**Architecture:** Build an isolated prototype under `spike/linked_document/`; production code in `engine/` remains untouched. The prototype separates PDF evidence extraction, conservative cover-letter classification, safe single-page candidate discovery, deterministic matching, and one exact-host adapter for Maruti's public JSON endpoint. A live probe scans a fixed, diverse company set, builds the corpus, runs the resolver, and emits an auditable JSON/Markdown gate report. If the gate fails, stop without integrating.

**Tech Stack:** Python 3.11+, existing `httpx==0.27.2`, existing `pypdf==4.3.1`, Python standard library, pytest.

---

## Scope and file map

The feasibility phase creates only these paths:

- `spike/linked_document/__init__.py` — public prototype surface.
- `spike/linked_document/models.py` — immutable evidence, candidate, response, and outcome types.
- `spike/linked_document/evidence.py` — PDF evidence extraction and conservative classification.
- `spike/linked_document/safety.py` — HTTPS/SSRF checks and bounded HTTP reads.
- `spike/linked_document/candidates.py` — static HTML discovery, period inference, deterministic scoring.
- `spike/linked_document/adapters.py` — exact-host adapter registry and Maruti JSON parser.
- `spike/linked_document/resolver.py` — one-hop orchestration and final PDF revalidation.
- `spike/linked_document/probe.py` — live BSE corpus builder and gate report writer.
- `spike/linked_document/tests/` — unit and integration-shaped tests using only local fixtures/mocks.
- `spike/linked_document/tests/fixtures/maruti_documents.json` — small recorded public JSON excerpt.
- `spike/linked_document/companies.json` — fixed company universe for reproducibility.
- `spike/downloads/linked-document-results.json` — ignored live-run evidence.
- `spike/LINKED_DOCUMENT_FINDINGS.md` — generated, human-readable gate result.

Do not modify `engine/`, `api/`, `ui/`, `worker/`, release metadata, or GitHub issues in this phase.

## Gate definition

The prototype may be recommended for later product integration only if the live report proves all of the following:

1. At least 15 confirmed link-only cover letters.
2. At least 5 issuers and at least 3 of: annual reports, concalls, investor presentations, financial results.
3. Detection recall of 15/15 on the confirmed cover-letter corpus.
4. Zero false positives among at least 30 controls, including genuine short PDFs.
5. KFin, HDFC Bank, and Maruti resolve end-to-end.
6. At least 80% of confirmed cases resolve, with no more than two exact-host adapters.
7. Ambiguous, unsafe, unsupported, or non-substantive replacements fail honestly.
8. A substantive BSE PDF causes zero landing-page requests.

If any required condition fails, record the failure and stop before product integration.

### Task 1: Establish the isolated prototype and baseline

**Files:**

- Create: `spike/linked_document/__init__.py`
- Create: `spike/linked_document/models.py`
- Create: `spike/linked_document/tests/__init__.py`
- Create: `spike/linked_document/tests/test_models.py`

- [ ] **Step 1: Verify the existing suite before introducing prototype code**

Run:

```bash
.venv/bin/python -m pytest -q
```

Expected: the current suite passes. Record exact counts in the execution notes; do not weaken or skip existing tests.

- [ ] **Step 2: Write the failing model-contract test**

```python
from datetime import date

from spike.linked_document.models import DocumentContext, PdfEvidence


def test_document_context_is_immutable_and_normalizes_no_input():
    context = DocumentContext(
        company="KFin Technologies",
        folder="annual-reports",
        filing_date=date(2026, 7, 28),
        headline="Annual Report for FY 2025-26",
        source_url="https://www.bseindia.com/xml-data/corpfiling/AttachLive/example.pdf",
    )
    evidence = PdfEvidence(page_count=2, text="The annual report is available here", links=("https://example.com/report",))

    assert context.folder == "annual-reports"
    assert evidence.page_count == 2
    assert evidence.links == ("https://example.com/report",)
```

Run:

```bash
.venv/bin/python -m pytest spike/linked_document/tests/test_models.py -q
```

Expected: FAIL because the package does not exist.

- [ ] **Step 3: Add the minimum immutable model types**

Define frozen dataclasses and literal statuses:

```python
@dataclass(frozen=True)
class DocumentContext:
    company: str
    folder: str
    filing_date: date
    headline: str
    source_url: str


@dataclass(frozen=True)
class PdfEvidence:
    page_count: int
    text: str
    links: tuple[str, ...]


@dataclass(frozen=True)
class Candidate:
    url: str
    label: str
    source: Literal["cover", "html", "adapter"]


@dataclass(frozen=True)
class HttpDocument:
    url: str
    content_type: str
    body: bytes


@dataclass(frozen=True)
class Resolution:
    status: Literal["substantive", "resolved", "unresolved"]
    reason: str
    source_url: str | None = None
    pdf: bytes | None = None
```

Export them from `__init__.py`.

- [ ] **Step 4: Run the model test and commit**

Run:

```bash
.venv/bin/python -m pytest spike/linked_document/tests/test_models.py -q
git add spike/linked_document
git commit -m "spike: establish linked document prototype"
```

Expected: PASS; local commit only.

### Task 2: Extract PDF evidence and detect cover letters conservatively

**Files:**

- Create: `spike/linked_document/evidence.py`
- Create: `spike/linked_document/tests/test_evidence.py`

- [ ] **Step 1: Write failing classifier tests first**

Cover these cases explicitly:

Create these complete tests, using ordinary assertions and a shared `context(folder)` helper:

- `test_detects_link_only_cover_letter_in_supported_folder`, parametrized over `annual-reports`, `concalls`, `investor-ppts`, and `quarterly`;
- `test_rejects_same_letter_in_arbitrary_folder`;
- `test_rejects_short_pdf_without_external_link`;
- `test_rejects_short_genuine_transcript_with_many_text_signals`;
- `test_rejects_long_document_even_if_it_mentions_company_website`;
- `test_extracts_page_count_text_and_uri_annotation_from_pdf`.

The positive evidence must combine all of:

- supported folder;
- no more than 3 pages;
- exchange/submission language such as `BSE`, `NSE`, `Regulation`, or `please find enclosed`;
- link-only language such as `available at`, `can be accessed`, `uploaded on`, or `web-link`;
- at least one external HTTPS link.

The negative genuine-transcript case must be 2 pages, contain no external link, and include dialogue/speaker markers so that page count alone can never classify it.

Run:

```bash
.venv/bin/python -m pytest spike/linked_document/tests/test_evidence.py -q
```

Expected: FAIL because extraction/classification is missing.

- [ ] **Step 2: Implement bounded evidence extraction**

Implement:

Add `SUPPORTED_FOLDERS = frozenset({"annual-reports", "concalls", "investor-ppts", "quarterly"})` and implement these public contracts:

- `extract_pdf_evidence(pdf: bytes, *, max_pages: int = 4) -> PdfEvidence` — read only the first `max_pages` for text/URI evidence while returning the total page count.
- `is_linked_cover_letter(context: DocumentContext, evidence: PdfEvidence) -> bool` — return true only when every conservative signal family is present.

Use `pypdf.PdfReader(BytesIO(pdf))`. Read URI annotations from `/Annots` `/A` `/URI`, collect visible `https://` URLs from extracted text, de-duplicate while preserving order, and cap extracted text at 30,000 characters.

Do not classify by byte size. Do not make network requests here.

- [ ] **Step 3: Run focused and regression tests, then commit**

```bash
.venv/bin/python -m pytest spike/linked_document/tests/test_evidence.py -q
.venv/bin/python -m pytest engine/tests/test_fetcher.py engine/tests/test_library.py -q
git add spike/linked_document
git commit -m "spike: detect linked filing cover letters"
```

Expected: both commands PASS.

### Task 3: Enforce safe, bounded external fetching

**Files:**

- Create: `spike/linked_document/safety.py`
- Create: `spike/linked_document/tests/test_safety.py`

- [ ] **Step 1: Write failing URL-policy tests**

Test acceptance of a normal public HTTPS hostname and rejection of:

- `http://`;
- embedded credentials;
- `localhost` and `.local`;
- literal loopback/private/link-local/multicast/reserved IPv4 and IPv6;
- a public-looking hostname whose injected DNS resolver returns a private address;
- more than 3 redirects;
- HTML larger than 3 MiB and PDF larger than 100 MiB.

The DNS resolver must be injectable so tests never depend on real DNS.

- [ ] **Step 2: Implement the policy and one bounded fetch primitive**

Define `UnsafeUrl(ValueError)` and `ResponseTooLarge(ValueError)`, then implement these public contracts:

- `validate_public_https_url(url: str, *, resolve: Callable[[str], Iterable[str]] = resolve_host) -> str`
- `fetch_public_document(client: httpx.Client, url: str, *, expected: Literal["html", "pdf"], max_redirects: int = 3) -> HttpDocument`

Validate every redirect target before following it. Stream in 64 KiB chunks and stop immediately above the applicable byte ceiling. Set a FilingForge-identifying user agent and explicit connect/read timeouts. This primitive may fetch exactly one landing page and one candidate PDF per resolution attempt.

- [ ] **Step 3: Verify and commit**

```bash
.venv/bin/python -m pytest spike/linked_document/tests/test_safety.py -q
git add spike/linked_document
git commit -m "spike: bound external document fetching"
```

Expected: PASS.

### Task 4: Discover and match static-page candidates deterministically

**Files:**

- Create: `spike/linked_document/candidates.py`
- Create: `spike/linked_document/tests/test_candidates.py`

- [ ] **Step 1: Write failing HTML and period-matching tests**

Use small inline KFin-like and HDFC-like HTML snippets. Test:

- relative links are joined to the landing URL;
- fragments, non-HTTPS schemes, duplicate URLs, and obvious non-PDF assets are excluded;
- `FY 2025-26` matches `FY2025-26`, `2025-2026`, and `FY26` tokens;
- a quarter ended 31 December 2025 maps to `Q3FY26`;
- a quarter ended 31 March 2026 maps to `Q4FY26`;
- annual-report candidates do not match presentations or transcripts;
- a unique best candidate is selected;
- tied best candidates return `None`, never the first item;
- a below-threshold candidate returns `None`.

- [ ] **Step 2: Implement standard-library HTML parsing and evidence scoring**

Expose:

Implement these public contracts:

- `parse_html_candidates(html: bytes, landing_url: str) -> tuple[Candidate, ...]`
- `infer_period_tokens(context: DocumentContext, cover_text: str) -> frozenset[str]`
- `select_unique_candidate(context: DocumentContext, cover_text: str, candidates: Sequence[Candidate]) -> Candidate | None`

Use `html.parser.HTMLParser` and `urllib.parse.urljoin`; add no dependency. Score transparent evidence families:

- required compatible document type: +6;
- exact quarter/FY token: +5;
- compatible date/year token: +2;
- incompatible document type: -10.

Require a score of at least 9 and a strictly unique maximum. Keep scoring data-driven and expose a helper returning component scores so the probe report can explain each decision.

- [ ] **Step 3: Verify and commit**

```bash
.venv/bin/python -m pytest spike/linked_document/tests/test_candidates.py -q
git add spike/linked_document
git commit -m "spike: match official filing candidates"
```

Expected: PASS.

### Task 5: Add the one known dynamic-host adapter

**Files:**

- Create: `spike/linked_document/adapters.py`
- Create: `spike/linked_document/tests/test_adapters.py`
- Create: `spike/linked_document/tests/fixtures/maruti_documents.json`

- [ ] **Step 1: Record a minimal public Maruti fixture**

Store only 3–5 representative `corporateDocumentsList` records needed to prove selection. Retain `title`, `description`, `year`, `yearRange`, `date`, and `pdfLink`; do not store cookies, tokens, personal data, or the full response.

- [ ] **Step 2: Write the failing exact-host adapter tests**

Prove:

- `www.marutisuzuki.com` uses the adapter;
- a lookalike/suffix hostname does not;
- the adapter emits transcript candidates from the recorded JSON;
- Q4 FY2025-26 selects the correct transcript;
- an adapter response with two equal candidates is unresolved.

- [ ] **Step 3: Implement a tiny registry and Maruti parser**

Define the registry as `ADAPTERS = {"www.marutisuzuki.com": maruti_candidates}` and implement these public contracts:

- `adapter_request(landing_url: str) -> tuple[str, Literal["html", "json"]] | None`
- `parse_adapter_candidates(hostname: str, document: HttpDocument) -> tuple[Candidate, ...]`

The Maruti request URL is the public Adobe AEM persisted-query endpoint already used by its corporate site:

```text
https://www.marutisuzuki.com/graphql/execute.json/msil-platform/corporateDocumentsList;documentCategory=companyReports
```

The registry must use the exact normalized hostname. Do not add an adapter for KFin or HDFC; both must use generic static HTML discovery. Do not add a second adapter during implementation merely to raise the score—if the live corpus needs more than two total, the gate fails and the design is reassessed.

- [ ] **Step 4: Verify and commit**

```bash
.venv/bin/python -m pytest spike/linked_document/tests/test_adapters.py -q
git add spike/linked_document
git commit -m "spike: support Maruti public document index"
```

Expected: PASS.

### Task 6: Orchestrate one-hop resolution and revalidate the replacement

**Files:**

- Create: `spike/linked_document/resolver.py`
- Create: `spike/linked_document/tests/test_resolver.py`

- [ ] **Step 1: Write failing orchestration tests with an injected fake fetcher**

Test the complete state machine:

1. A substantive original PDF returns `substantive`, the original bytes, and makes zero fetch calls.
2. A KFin-style cover letter with a direct substantive PDF link resolves with one PDF request.
3. A KFin/HDFC static landing page resolves with one landing request and one PDF request.
4. A Maruti cover letter resolves through the adapter endpoint and then one PDF request.
5. A candidate replacement that is itself another cover letter returns `unresolved`.
6. A non-PDF response returns `unresolved`.
7. An ambiguous candidate list returns `unresolved` without downloading either candidate.
8. An unsafe cover link returns `unresolved` without a request.
9. A supported-folder cover letter with no resolvable candidate returns `unresolved`; it never returns the cover letter as a successful requested document.

- [ ] **Step 2: Implement the state machine**

Implement `resolve_document(context: DocumentContext, original_pdf: bytes, *, fetch: Callable[[str, Literal["html", "pdf", "json"]], HttpDocument]) -> Resolution`.

Required behavior:

- Extract evidence once and return immediately for a substantive original.
- Consider only HTTPS links already present in the cover-letter text/annotations.
- If a link itself is a PDF, fetch it directly; otherwise fetch one landing resource.
- Use the exact-host adapter when registered; otherwise parse static HTML.
- Require deterministic unique selection.
- Verify `%PDF-`, parseability, and that the replacement no longer classifies as a cover letter.
- Preserve the original BSE filing identity in `DocumentContext`; `source_url` on the result records provenance only.
- Catch expected safety/network/parse failures and return a precise unresolved reason. Do not swallow programming errors.

- [ ] **Step 3: Run all prototype tests and existing download regressions**

```bash
.venv/bin/python -m pytest spike/linked_document/tests -q
.venv/bin/python -m pytest engine/tests/test_fetcher.py engine/tests/test_library.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add spike/linked_document
git commit -m "spike: resolve linked filing documents"
```

### Task 7: Build the live 15-case corpus and 30-control gate

**Files:**

- Create: `spike/linked_document/companies.json`
- Create: `spike/linked_document/probe.py`
- Create: `spike/linked_document/tests/test_probe.py`

- [ ] **Step 1: Add a fixed, diverse company universe**

The JSON registry must include these 45 known BSE scrip codes so the run is reproducible and is not tuned only to the three known examples:

```text
KFINTECH 543720, MARUTI 532500, HDFCBANK 500180, TANLA 532790,
RELIANCE 500325, ITC 500875, TITAN 500114, KAYNES 543664,
ETERNAL 543320, TCS 532540, INFY 500209, WIPRO 507685,
ICICIBANK 532174, SBIN 500112, SUNPHARMA 524715, BHARTIARTL 532454,
HINDUNILVR 500696, BAJFINANCE 500034, ASIANPAINT 500820, LT 500510,
ADANIENT 512599, DMART 540376, PIDILITIND 500331, M&M 500520,
TRENT 500251, NBCC 534309, PAISALO 532900, ESCORTS 500495,
HCLTECH 532281, AXISBANK 532215, KOTAKBANK 500247, BAJAJFINSV 532978,
ULTRACEMCO 532538, NESTLEIND 500790, POWERGRID 532898, NTPC 532555,
ONGC 500312, COALINDIA 533278, TECHM 532755, DRREDDY 500124,
CIPLA 500087, TATASTEEL 500470, JSWSTEEL 500228, GRASIM 500300,
HINDALCO 500440
```

- [ ] **Step 2: Write failing probe-unit tests**

Using recorded small BSE API payloads/fake responses, prove that the probe:

- maps only the four scoped categories;
- selects suspected cover letters using the production-shaped classifier, not byte size;
- deliberately retains genuine small PDFs as controls;
- de-duplicates by BSE `NEWSID`;
- caps requests per company/date window;
- calculates recall, false positives, issuer/category coverage, resolution rate, required-host results, adapter count, and normal-path fetch count;
- reports `PASS` only when every gate condition is true.

- [ ] **Step 3: Implement the bounded live probe**

CLI:

```bash
.venv/bin/python -m spike.linked_document.probe \
  --from-date 2024-04-01 \
  --to-date 2026-08-23 \
  --minimum-cover-letters 15 \
  --minimum-companies 5 \
  --minimum-categories 3 \
  --controls 30 \
  --output spike/downloads/linked-document-results.json \
  --markdown spike/LINKED_DOCUMENT_FINDINGS.md
```

Implementation constraints:

- Reuse `engine.bse_client.BSEClient` and call `engine.fetcher.list_filings` with the four matching entries from `engine.models.CURATED`; do not fork category rules.
- Search only the fixed dates and companies, with a small delay between BSE requests.
- Download only scoped candidate attachments; cap attachment size before parsing.
- First pass automatically labels suspects by the conservative detector and samples controls from detector negatives, deliberately including documents with 1–3 pages.
- Second pass resolves all suspects and records every request, score component, selected URL, final page count/size, and failure reason.
- Seed the report with the already confirmed KFin, HDFC, and Maruti BSE source URLs if they are within the window; still process them through the same detector/resolver.
- Never log query credentials, headers, tokens, cookies, or local environment values.
- Write JSON under ignored `spike/downloads/`; write a compact Markdown table and gate verdict to `spike/LINKED_DOCUMENT_FINDINGS.md`.
- If fewer than 15 suspects, fewer than 5 issuers, or fewer than 3 categories are found in this fixed universe, record `INSUFFICIENT CORPUS` and fail the gate. Do not silently weaken the sample requirement.

- [ ] **Step 4: Verify probe logic and commit before the live run**

```bash
.venv/bin/python -m pytest spike/linked_document/tests/test_probe.py -q
.venv/bin/python -m pytest spike/linked_document/tests -q
git add spike/linked_document
git commit -m "spike: add linked document feasibility probe"
```

Expected: PASS.

### Task 8: Execute the live gate and audit the results

**Files:**

- Generate: `spike/downloads/linked-document-results.json`
- Generate/update: `spike/LINKED_DOCUMENT_FINDINGS.md`

- [ ] **Step 1: Run the fixed live probe**

Run the CLI from Task 7. Stream progress at least once per company so a long run is observable. Do not retry indefinitely; use two attempts only for transient BSE/network failures and record exhausted failures.

Expected: a complete JSON audit and Markdown gate report, whether the verdict is pass or fail.

- [ ] **Step 2: Manually validate corpus labels before trusting metrics**

For every detector-positive case, inspect the extracted first-page text, links, page count, source BSE URL, and resolved target metadata. Mark it confirmed only when it truly delegates the scoped document to an external link. Inspect all short (1–3 page) controls and a random sample of longer controls. Corrections must be explicit fields in the JSON report (`reviewed_label`, `review_note`); do not alter detector output to make metrics look better.

- [ ] **Step 3: Recompute the gate from reviewed labels**

Run:

```bash
.venv/bin/python -m spike.linked_document.probe \
  --report-only spike/downloads/linked-document-results.json \
  --markdown spike/LINKED_DOCUMENT_FINDINGS.md
```

Expected: the Markdown report contains exact denominators, false positives, unresolved cases, hostname/adapter counts, request counts, timings, and a single `PASS`, `FAIL`, or `INSUFFICIENT CORPUS` verdict.

- [ ] **Step 4: Run full verification**

```bash
.venv/bin/python -m pytest spike/linked_document/tests -q
.venv/bin/python -m pytest -q
git diff --check
git status --short
```

Expected: prototype tests and the full existing suite pass; no whitespace errors; only intended prototype/findings/plan changes are present.

- [ ] **Step 5: Commit the audited findings locally**

```bash
git add spike/LINKED_DOCUMENT_FINDINGS.md spike/linked_document
git commit -m "spike: record linked document feasibility results"
```

Do not add `spike/downloads/linked-document-results.json`; it is local evidence and may contain large/public-source artifacts. Do not push.

### Task 9: Stop at the decision boundary

- [ ] **If the verdict is PASS:** report the exact results and propose a separate production-integration plan that wires the proven resolver into `engine/fetcher.py`, adds progress/error UX, and preserves original BSE filenames/identity. Do not integrate until the user reviews the evidence.

- [ ] **If the verdict is FAIL or INSUFFICIENT CORPUS:** report exactly which gate condition failed and whether the evidence supports detection-only, a narrower hostname allowlist, or abandoning the fallback. Do not add adapters or loosen thresholds during this phase.

- [ ] Revisit the wording for GitHub issues #21 and #22 only after reporting the feasibility outcome. Do not post replies without explicit approval.

## Plan self-review

- The work is isolated from the production engine and therefore cannot change current user downloads.
- Every behavior begins with a failing test and a focused pass before broader regression runs.
- Detection never uses file size alone.
- Static parsing and one exact-host adapter cover the three known cases without browser automation.
- Network behavior is bounded to the suspect path and protected against SSRF/redirect abuse.
- Ambiguity and unsupported sites fail honestly.
- The live gate cannot pass by shrinking denominators or omitting difficult cases.
- The task ends before integration, release, push, deployment, or GitHub replies.
