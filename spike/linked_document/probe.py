from __future__ import annotations

import argparse
import json
import math
import time
from collections.abc import Iterable, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from pypdf.errors import PdfReadError

from engine.bse_client import BSEClient, HEADERS
from engine.errors import FilingForgeError
from engine.fetcher import list_filings
from engine.models import CURATED, CategorySpec, Filing

from .adapters import adapter_request
from .evidence import external_https_links, extract_pdf_evidence, is_linked_cover_letter
from .models import DocumentContext
from .resolver import resolve_document
from .safety import fetch_public_document

COMPANIES_PATH = Path(__file__).with_name("companies.json")
_BSE_PDF_BASES = (
    "https://www.bseindia.com/xml-data/corpfiling/AttachHis/",
    "https://www.bseindia.com/xml-data/corpfiling/AttachLive/",
)
_SCOPED_KEYS = frozenset({"annual_report", "results", "investor_ppt", "concall"})
_MAX_BSE_PDF_BYTES = 5 * 1024 * 1024
_MAX_FILINGS_PER_COMPANY = 40


def category_specs() -> list[CategorySpec]:
    return [spec for spec in CURATED if spec.key in _SCOPED_KEYS]


def load_companies(path: Path = COMPANIES_PATH) -> list[dict[str, str]]:
    return json.loads(path.read_text(encoding="utf-8"))


def deduplicate_filings(filings: Iterable[Filing]) -> list[Filing]:
    seen: set[str] = set()
    unique: list[Filing] = []
    for filing in filings:
        if filing.news_id in seen:
            continue
        seen.add(filing.news_id)
        unique.append(filing)
    return unique


def select_controls(records: Sequence[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    controls = [record for record in records if not record["detected"]]
    controls.sort(key=lambda record: (0 if 1 <= int(record["page_count"]) <= 3 else 1, int(record["page_count"])))
    return controls[:limit]


def compute_gate(
    records: Sequence[dict[str, Any]],
    *,
    adapter_hosts: set[str],
    normal_path_requests: int,
    minimum_cover_letters: int,
    minimum_companies: int,
    minimum_categories: int,
    minimum_controls: int,
) -> dict[str, Any]:
    covers = [record for record in records if record.get("reviewed_label") == "cover"]
    controls = [record for record in records if record.get("reviewed_label") == "control"]
    detected_covers = sum(bool(record.get("detected")) for record in covers)
    false_positives = sum(bool(record.get("detected")) for record in controls)
    resolved = sum(record.get("resolution_status") == "resolved" for record in covers)
    cover_companies = {record["company"] for record in covers}
    cover_categories = {record["folder"] for record in covers}
    required_needles = ("kfin", "hdfc", "maruti")
    required_resolved = {
        needle: any(
            needle in record["company"].lower() and record.get("resolution_status") == "resolved"
            for record in covers
        )
        for needle in required_needles
    }
    recall = detected_covers / len(covers) if covers else 0.0
    resolution_rate = resolved / len(covers) if covers else 0.0
    corpus_ok = (
        len(covers) >= minimum_cover_letters
        and len(controls) >= minimum_controls
        and len(cover_companies) >= minimum_companies
        and len(cover_categories) >= minimum_categories
    )
    conditions = {
        "all_covers_detected": bool(covers) and detected_covers == len(covers),
        "zero_control_false_positives": false_positives == 0,
        "required_issuers_resolved": all(required_resolved.values()),
        "resolution_rate_at_least_80_percent": resolution_rate >= 0.8,
        "no_more_than_two_adapters": len(adapter_hosts) <= 2,
        "normal_path_has_zero_requests": normal_path_requests == 0,
    }
    if not corpus_ok:
        verdict = "INSUFFICIENT CORPUS"
    elif all(conditions.values()):
        verdict = "PASS"
    else:
        verdict = "FAIL"
    return {
        "verdict": verdict,
        "cover_letters": len(covers),
        "controls": len(controls),
        "cover_companies": len(cover_companies),
        "cover_categories": len(cover_categories),
        "detected_covers": detected_covers,
        "detection_recall": recall,
        "false_positives": false_positives,
        "resolved": resolved,
        "resolution_rate": resolution_rate,
        "adapter_hosts": sorted(adapter_hosts),
        "adapter_count": len(adapter_hosts),
        "normal_path_requests": normal_path_requests,
        "required_issuers": required_resolved,
        "conditions": conditions,
    }


def _attachment_urls(filing: Filing) -> tuple[str, ...]:
    if filing.attachment.startswith(("https://", "http://")):
        return (filing.attachment,)
    return tuple(base + filing.attachment for base in _BSE_PDF_BASES)


def _fetch_bse_pdf(
    client: httpx.Client,
    filing: Filing,
    *,
    maximum_bytes: int = _MAX_BSE_PDF_BYTES,
) -> tuple[bytes, str] | None:
    for url in _attachment_urls(filing):
        try:
            with client.stream("GET", url) as response:
                if response.status_code != 200:
                    continue
                declared = response.headers.get("Content-Length")
                if declared and int(declared) > maximum_bytes:
                    continue
                body = bytearray()
                for chunk in response.iter_bytes(chunk_size=64 * 1024):
                    body.extend(chunk)
                    if len(body) > maximum_bytes:
                        break
                if len(body) <= maximum_bytes and body.startswith(b"%PDF-"):
                    return bytes(body), str(response.url)
        except (httpx.HTTPError, ValueError):
            continue
    return None


def _context(company: dict[str, str], filing: Filing, source_url: str) -> DocumentContext:
    return DocumentContext(
        company=company["name"],
        folder=filing.folder,
        filing_date=date.fromisoformat(filing.date[:10]),
        headline=filing.headline,
        source_url=source_url,
    )


def _record(
    company: dict[str, str],
    filing: Filing,
    source_url: str,
    pdf: bytes,
) -> tuple[dict[str, Any], bytes] | None:
    try:
        evidence = extract_pdf_evidence(pdf)
    except (PdfReadError, ValueError, OSError):
        return None
    context = _context(company, filing, source_url)
    detected = is_linked_cover_letter(context, evidence)
    return (
        {
            "company": company["name"],
            "symbol": company["symbol"],
            "scrip_code": company["scrip_code"],
            "news_id": filing.news_id,
            "filing_date": filing.date[:10],
            "folder": filing.folder,
            "category": filing.category,
            "headline": filing.headline,
            "bse_source_url": source_url,
            "page_count": evidence.page_count,
            "original_bytes": len(pdf),
            "extracted_text": evidence.text[:4_000],
            "links": list(evidence.links),
            "detected": detected,
            "suggested_label": "cover" if detected else "control",
            "reviewed_label": None,
            "review_note": "",
            "resolution_status": "pending" if detected else "substantive",
            "resolution_reason": "",
            "resolved_url": None,
            "resolved_page_count": None,
            "resolved_bytes": None,
            "external_requests": [],
            "elapsed_seconds": 0.0,
        },
        pdf,
    )


def _resolve_record(
    record: dict[str, Any],
    pdf: bytes,
    external_client: httpx.Client,
) -> set[str]:
    requests: list[dict[str, Any]] = []

    def fetch(url: str, expected: str):
        started = time.perf_counter()
        try:
            return fetch_public_document(external_client, url, expected=expected)  # type: ignore[arg-type]
        finally:
            requests.append(
                {"url": url, "expected": expected, "elapsed_seconds": round(time.perf_counter() - started, 3)}
            )

    context = DocumentContext(
        company=record["company"],
        folder=record["folder"],
        filing_date=date.fromisoformat(record["filing_date"]),
        headline=record["headline"],
        source_url=record["bse_source_url"],
    )
    started = time.perf_counter()
    result = resolve_document(context, pdf, fetch=fetch)
    record["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    record["external_requests"] = requests
    record["resolution_status"] = result.status
    record["resolution_reason"] = result.reason
    record["resolved_url"] = result.source_url
    if result.pdf:
        record["resolved_bytes"] = len(result.pdf)
        try:
            record["resolved_page_count"] = extract_pdf_evidence(result.pdf).page_count
        except (PdfReadError, ValueError, OSError):
            record["resolved_page_count"] = None

    used_adapters: set[str] = set()
    original_links = record.get("links") or []
    for link in original_links:
        if adapter_request(link) is not None:
            host = httpx.URL(link).host
            if host:
                used_adapters.add(host)
    return used_adapters


def scan(
    *,
    from_date: date,
    to_date: date,
    minimum_cover_letters: int,
    minimum_companies: int,
    minimum_categories: int,
    controls: int,
) -> dict[str, Any]:
    companies = load_companies()
    specs = category_specs()
    years = max(1, math.ceil((date.today() - from_date).days / 365))
    candidates: list[tuple[dict[str, Any], bytes]] = []
    errors: list[dict[str, str]] = []
    adapter_hosts: set[str] = set()

    bse = BSEClient(rate_delay=0.1, max_retries=1, retry_backoff=0.25)
    bse_http = httpx.Client(headers=HEADERS, follow_redirects=True, timeout=httpx.Timeout(30.0, connect=10.0))
    external_http = httpx.Client(follow_redirects=False, timeout=httpx.Timeout(30.0, connect=10.0))
    try:
        for index, company in enumerate(companies, start=1):
            print(f"[{index}/{len(companies)}] {company['symbol']}: listing", flush=True)
            try:
                filings = list_filings(company["scrip_code"], specs, years, bse)
            except FilingForgeError as exc:
                errors.append({"company": company["name"], "stage": "listing", "error": str(exc)})
                continue
            filings = [
                filing
                for filing in deduplicate_filings(filings)
                if from_date.isoformat() <= filing.date[:10] <= to_date.isoformat()
            ][:_MAX_FILINGS_PER_COMPANY]
            found = 0
            for filing in filings:
                downloaded = _fetch_bse_pdf(bse_http, filing)
                if downloaded is None:
                    continue
                pdf, source_url = downloaded
                built = _record(company, filing, source_url, pdf)
                if built is not None:
                    candidates.append(built)
                    found += 1
            detected = sum(record["detected"] for record, _pdf in candidates)
            cover_records = [record for record, _pdf in candidates if record["detected"]]
            cover_companies = {record["company"] for record in cover_records}
            cover_categories = {record["folder"] for record in cover_records}
            negatives = sum(not record["detected"] for record, _pdf in candidates)
            print(
                f"[{index}/{len(companies)}] {company['symbol']}: inspected {found}; "
                f"suspects={detected}, controls={negatives}",
                flush=True,
            )
            if (
                detected >= minimum_cover_letters
                and len(cover_companies) >= minimum_companies
                and len(cover_categories) >= minimum_categories
                and negatives >= controls * 2
            ):
                break

        suspects = [(record, pdf) for record, pdf in candidates if record["detected"]]
        negative_records = [record for record, _pdf in candidates if not record["detected"]]
        selected_control_records = select_controls(negative_records, controls)
        selected_ids = {record["news_id"] for record in selected_control_records}
        selected_controls = [
            (record, pdf)
            for record, pdf in candidates
            if not record["detected"] and record["news_id"] in selected_ids
        ]

        for number, (record, pdf) in enumerate(suspects, start=1):
            print(f"[resolve {number}/{len(suspects)}] {record['company']} — {record['headline'][:55]}", flush=True)
            try:
                adapter_hosts.update(_resolve_record(record, pdf, external_http))
            except Exception as exc:
                record["resolution_status"] = "unresolved"
                record["resolution_reason"] = f"unexpected resolver error: {type(exc).__name__}: {exc}"

        normal_path_requests = 0
        for record, pdf in selected_controls:
            def unexpected_fetch(_url: str, _expected: str):
                nonlocal normal_path_requests
                normal_path_requests += 1
                raise AssertionError("substantive control attempted an external request")

            context = DocumentContext(
                company=record["company"],
                folder=record["folder"],
                filing_date=date.fromisoformat(record["filing_date"]),
                headline=record["headline"],
                source_url=record["bse_source_url"],
            )
            outcome = resolve_document(context, pdf, fetch=unexpected_fetch)
            record["resolution_status"] = outcome.status
            record["resolution_reason"] = outcome.reason

        output_records = [record for record, _pdf in suspects + selected_controls]
        return {
            "run": {
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
                "companies_considered": len(companies),
                "companies_scanned": index,
                "scoped_categories": [spec.folder for spec in specs],
                "maximum_bse_pdf_bytes": _MAX_BSE_PDF_BYTES,
                "maximum_filings_per_company": _MAX_FILINGS_PER_COMPANY,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            "requirements": {
                "minimum_cover_letters": minimum_cover_letters,
                "minimum_companies": minimum_companies,
                "minimum_categories": minimum_categories,
                "minimum_controls": controls,
            },
            "adapter_hosts": sorted(adapter_hosts),
            "normal_path_requests": normal_path_requests,
            "errors": errors,
            "records": output_records,
        }
    finally:
        bse.close()
        bse_http.close()
        external_http.close()


def metrics_for_payload(payload: dict[str, Any]) -> dict[str, Any]:
    requirements = payload["requirements"]
    return compute_gate(
        payload["records"],
        adapter_hosts=set(payload.get("adapter_hosts", [])),
        normal_path_requests=int(payload.get("normal_path_requests", 0)),
        minimum_cover_letters=int(requirements["minimum_cover_letters"]),
        minimum_companies=int(requirements["minimum_companies"]),
        minimum_categories=int(requirements["minimum_categories"]),
        minimum_controls=int(requirements["minimum_controls"]),
    )


def render_markdown(payload: dict[str, Any]) -> str:
    metrics = metrics_for_payload(payload)
    unreviewed = sum(record.get("reviewed_label") is None for record in payload["records"])
    displayed_verdict = "REVIEW REQUIRED" if unreviewed else metrics["verdict"]
    lines = [
        "# Linked-Document Fallback Feasibility Findings",
        "",
        f"**Verdict: {displayed_verdict}**",
        "",
        f"Live window: {payload['run']['from_date']} to {payload['run']['to_date']}. "
        f"Companies scanned: {payload['run']['companies_scanned']}. Unreviewed records: {unreviewed}.",
        "",
        "| Metric | Result |",
        "|---|---:|",
        f"| Confirmed cover letters | {metrics['cover_letters']} |",
        f"| Confirmed controls | {metrics['controls']} |",
        f"| Cover-letter issuers | {metrics['cover_companies']} |",
        f"| Cover-letter categories | {metrics['cover_categories']} |",
        f"| Detection recall | {metrics['detection_recall']:.1%} |",
        f"| False positives | {metrics['false_positives']} |",
        f"| Resolution rate | {metrics['resolution_rate']:.1%} |",
        f"| Exact-host adapters used | {metrics['adapter_count']} |",
        f"| Normal-path external requests | {metrics['normal_path_requests']} |",
        "",
        "## Cases",
        "",
        "| Company | Date | Type | Pages | Detected | Review | Resolution | Source |",
        "|---|---|---|---:|---|---|---|---|",
    ]
    for record in payload["records"]:
        source = record["bse_source_url"]
        lines.append(
            f"| {record['company']} | {record['filing_date']} | {record['folder']} | "
            f"{record['page_count']} | {record['detected']} | {record.get('reviewed_label') or 'pending'} | "
            f"{record['resolution_status']} | [BSE]({source}) |"
        )
    if payload.get("errors"):
        lines.extend(["", "## Scan errors", ""])
        lines.extend(
            f"- {error['company']} ({error['stage']}): {error['error']}" for error in payload["errors"]
        )
    return "\n".join(lines) + "\n"


def _write_outputs(payload: dict[str, Any], output: Path, markdown: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown.write_text(render_markdown(payload), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the linked-document feasibility gate")
    parser.add_argument("--from-date", default="2024-04-01")
    parser.add_argument("--to-date", default="2026-08-23")
    parser.add_argument("--minimum-cover-letters", type=int, default=15)
    parser.add_argument("--minimum-companies", type=int, default=5)
    parser.add_argument("--minimum-categories", type=int, default=3)
    parser.add_argument("--controls", type=int, default=30)
    parser.add_argument("--output", type=Path, default=Path("spike/downloads/linked-document-results.json"))
    parser.add_argument("--markdown", type=Path, default=Path("spike/LINKED_DOCUMENT_FINDINGS.md"))
    parser.add_argument("--report-only", type=Path)
    args = parser.parse_args(argv)

    if args.report_only:
        payload = json.loads(args.report_only.read_text(encoding="utf-8"))
        _write_outputs(payload, args.report_only, args.markdown)
    else:
        payload = scan(
            from_date=date.fromisoformat(args.from_date),
            to_date=date.fromisoformat(args.to_date),
            minimum_cover_letters=args.minimum_cover_letters,
            minimum_companies=args.minimum_companies,
            minimum_categories=args.minimum_categories,
            controls=args.controls,
        )
        _write_outputs(payload, args.output, args.markdown)
    print(render_markdown(payload).splitlines()[2], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
