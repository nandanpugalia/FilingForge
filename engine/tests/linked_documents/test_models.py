from dataclasses import FrozenInstanceError
from datetime import date
from importlib import import_module

import pytest


def test_document_models_preserve_input_and_are_immutable():
    models = import_module("engine.linked_documents.models")
    context = models.DocumentContext(
        company="KFin Technologies",
        folder="annual-reports",
        filing_date=date(2026, 7, 28),
        headline="Annual Report for FY 2025-26",
        source_url="https://www.bseindia.com/xml-data/corpfiling/AttachLive/example.pdf",
    )
    evidence = models.PdfEvidence(
        page_count=2,
        text="The annual report is available here",
        links=("https://example.com/report",),
    )

    assert context.folder == "annual-reports"
    assert evidence.page_count == 2
    assert evidence.links == ("https://example.com/report",)
    with pytest.raises(FrozenInstanceError):
        context.folder = "concalls"
