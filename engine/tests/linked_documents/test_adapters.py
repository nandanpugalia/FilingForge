import json
from datetime import date
from importlib import import_module
from pathlib import Path

from engine.linked_documents.candidates import select_unique_candidate
from engine.linked_documents.models import DocumentContext, HttpDocument

FIXTURE = Path(__file__).parent / "fixtures" / "maruti_documents.json"


def context() -> DocumentContext:
    return DocumentContext(
        company="Maruti Suzuki India Limited",
        folder="concalls",
        filing_date=date(2026, 5, 4),
        headline="Earnings Call Transcript",
        source_url="https://www.bseindia.com/example.pdf",
    )


def test_exact_maruti_hostname_uses_public_json_adapter():
    adapters = import_module("engine.linked_documents.adapters")

    assert adapters.adapter_request("https://www.marutisuzuki.com/corporate/investors") == (
        adapters.MARUTI_DOCUMENTS_URL,
        "json",
    )
    assert adapters.adapter_request("https://www.marutisuzuki.com.evil.example/investors") is None


def test_parses_maruti_transcript_candidates_and_selects_q4():
    adapters = import_module("engine.linked_documents.adapters")
    document = HttpDocument(
        url=adapters.MARUTI_DOCUMENTS_URL,
        content_type="application/json",
        body=FIXTURE.read_bytes(),
    )

    candidates = adapters.parse_adapter_candidates("www.marutisuzuki.com", document)
    selected = select_unique_candidate(
        context(),
        "Transcript for the quarter and year ended March 31, 2026 can be accessed here.",
        candidates,
    )

    assert len(candidates) == 3
    assert selected is not None
    assert selected.source == "adapter"
    assert selected.url.startswith("https://www.marutisuzuki.com/content/dam/")
    assert "Q4_FY_26.pdf" in selected.url


def test_duplicate_maruti_records_remain_ambiguous():
    adapters = import_module("engine.linked_documents.adapters")
    payload = json.loads(FIXTURE.read_text())
    items = payload["data"]["corporateDocumentsList"]["items"]
    duplicate = dict(items[1])
    duplicate["pdfLink"] = {"_publishUrl": "https://cdn.example.com/duplicate_Q4_FY_26.pdf"}
    items.append(duplicate)
    document = HttpDocument(
        url=adapters.MARUTI_DOCUMENTS_URL,
        content_type="application/json",
        body=json.dumps(payload).encode(),
    )

    candidates = adapters.parse_adapter_candidates("www.marutisuzuki.com", document)

    assert select_unique_candidate(
        context(),
        "Transcript for the quarter and year ended March 31, 2026 can be accessed here.",
        candidates,
    ) is None
