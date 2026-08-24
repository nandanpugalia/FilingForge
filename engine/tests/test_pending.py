import json
from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, RectangleObject

from engine.models import Filing, PendingDocument
from engine.organiser import record_seen
from engine.pending import (PendingImportError, import_pending_pdf, list_pending,
                            remove_pending, upsert_pending)


def item(news_id: str = "news-1", *, reason: str = "ambiguous issuer page") -> PendingDocument:
    return PendingDocument(
        news_id=news_id,
        date="2026-07-28",
        headline="Annual Report FY 2025-26",
        folder="annual-reports",
        category="Annual Reports",
        expected_type="Annual report",
        expected_period="FY 2025-26",
        bse_url="https://www.bseindia.com/xml-data/corpfiling/AttachHis/notice.pdf",
        issuer_url="https://investor.example.com/annual-reports/",
        reason=reason,
    )


def test_pending_ledger_round_trips_version_one(tmp_path):
    company = tmp_path / "KFINTECH"
    upsert_pending(company, item())

    assert list_pending(company) == [item()]
    raw = json.loads((company / ".filingforge_pending.json").read_text(encoding="utf-8"))
    assert raw["version"] == 1
    assert raw["items"][0]["news_id"] == "news-1"


def test_upsert_replaces_same_news_id_without_duplicate(tmp_path):
    company = tmp_path / "KFINTECH"
    upsert_pending(company, item())
    upsert_pending(company, item(reason="replacement download failed"))

    pending = list_pending(company)
    assert len(pending) == 1
    assert pending[0].reason == "replacement download failed"


def test_remove_unknown_id_fails_without_rewriting_ledger(tmp_path):
    company = tmp_path / "KFINTECH"
    upsert_pending(company, item())
    ledger = company / ".filingforge_pending.json"
    before = ledger.read_bytes()

    with pytest.raises(KeyError, match="missing"):
        remove_pending(company, "missing")

    assert ledger.read_bytes() == before


def test_removing_last_pending_item_removes_ledger(tmp_path):
    company = tmp_path / "KFINTECH"
    upsert_pending(company, item())

    remove_pending(company, "news-1")

    assert list_pending(company) == []
    assert not (company / ".filingforge_pending.json").exists()


@pytest.mark.parametrize("payload", [
    "{not json",
    json.dumps({"version": 99, "items": []}),
])
def test_corrupt_or_unknown_ledger_reads_empty_without_being_overwritten(tmp_path, payload):
    company = tmp_path / "KFINTECH"
    company.mkdir()
    ledger = company / ".filingforge_pending.json"
    ledger.write_text(payload, encoding="utf-8")
    before = ledger.read_bytes()

    assert list_pending(company) == []
    assert ledger.read_bytes() == before


def test_news_id_is_data_not_a_path(tmp_path):
    company = tmp_path / "KFINTECH"
    dangerous = item("../../outside")

    upsert_pending(company, dangerous)

    assert list_pending(company)[0].news_id == "../../outside"
    assert not (tmp_path / "outside").exists()


def test_tampered_pending_folder_is_rejected_without_escaping_company(tmp_path):
    company = tmp_path / "KFINTECH"
    company.mkdir()
    dangerous = {**item().__dict__, "folder": "../../outside"}
    ledger = company / ".filingforge_pending.json"
    ledger.write_text(json.dumps({"version": 1, "items": [dangerous]}), encoding="utf-8")
    before = ledger.read_bytes()

    assert list_pending(company) == []
    assert ledger.read_bytes() == before
    assert not (tmp_path / "outside").exists()


def make_pdf(text: str = "Complete annual report with substantive financial discussion", *,
             pages: int = 4, link: str | None = None) -> bytes:
    writer = PdfWriter()
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    font_ref = writer._add_object(font)
    for index in range(pages):
        page = writer.add_blank_page(width=612, height=792)
        if index == 0:
            escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream = DecodedStreamObject()
            stream.set_data(f"BT /F1 10 Tf 40 740 Td ({escaped}) Tj ET".encode("latin-1"))
            page[NameObject("/Resources")] = DictionaryObject(
                {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
            )
            page[NameObject("/Contents")] = writer._add_object(stream)
    if link:
        writer.add_uri(0, link, RectangleObject((0, 0, 40, 20)))
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_import_copies_source_into_slot_converts_indexes_and_marks_seen(tmp_path):
    company = tmp_path / "library" / "KFINTECH"
    upsert_pending(company, item())
    source = tmp_path / "Downloads" / "annual-report.pdf"
    source.parent.mkdir()
    original = make_pdf()
    source.write_bytes(original)

    destination = import_pending_pdf(company, "news-1", source)

    assert source.read_bytes() == original
    assert destination.parent == company / "annual-reports" / "2026"
    assert destination.name.endswith("__news-1.pdf")
    assert destination.read_bytes() == original
    assert destination.with_suffix(".md").exists()
    assert "news_id: news-1" in destination.with_suffix(".md").read_text(encoding="utf-8")
    assert json.loads((company / ".filingforge_index.json").read_text()) == ["news-1"]
    assert list_pending(company) == []
    assert destination.name in (company / "INDEX.md").read_text(encoding="utf-8")
    assert "KFINTECH" in (company.parent / "INDEX.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("content", [b"not a pdf", b"%PDF-broken"])
def test_import_rejects_non_pdf_or_unreadable_pdf_and_keeps_slot(tmp_path, content):
    company = tmp_path / "library" / "KFINTECH"
    upsert_pending(company, item())
    source = tmp_path / "bad.pdf"
    source.write_bytes(content)

    with pytest.raises(PendingImportError):
        import_pending_pdf(company, "news-1", source)

    assert list_pending(company) == [item()]
    assert list(company.rglob("*.pdf")) == []


def test_import_rejects_another_cover_letter(tmp_path):
    company = tmp_path / "library" / "KFINTECH"
    upsert_pending(company, item())
    source = tmp_path / "cover.pdf"
    source.write_bytes(make_pdf(
        "BSE Limited pursuant to Regulation annual report is available at the following link",
        pages=2,
        link="https://investor.example.com/report",
    ))

    with pytest.raises(PendingImportError, match="cover letter"):
        import_pending_pdf(company, "news-1", source)

    assert list_pending(company) == [item()]


def test_import_rejects_file_above_limit_without_reading_it(tmp_path, monkeypatch):
    import engine.pending as pending
    company = tmp_path / "library" / "KFINTECH"
    upsert_pending(company, item())
    source = tmp_path / "large.pdf"
    source.write_bytes(make_pdf())
    monkeypatch.setattr(pending, "PDF_MAX_BYTES", 10)

    with pytest.raises(PendingImportError, match="too large"):
        import_pending_pdf(company, "news-1", source)

    assert list_pending(company) == [item()]


def test_import_reads_from_one_bounded_open_handle_not_path_read_bytes(tmp_path, monkeypatch):
    company = tmp_path / "library" / "KFINTECH"
    upsert_pending(company, item())
    source = tmp_path / "report.pdf"
    source.write_bytes(make_pdf())
    original_read_bytes = Path.read_bytes

    def reject_unbounded_read(path: Path):
        if path == source:
            raise AssertionError("source.read_bytes is an unbounded second path lookup")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", reject_unbounded_read)

    destination = import_pending_pdf(company, "news-1", source)

    assert destination.exists()


def test_conversion_failure_rolls_back_library_and_keeps_source_and_slot(tmp_path, monkeypatch):
    import engine.pending as pending
    company = tmp_path / "library" / "KFINTECH"
    upsert_pending(company, item())
    source = tmp_path / "report.pdf"
    original = make_pdf()
    source.write_bytes(original)
    monkeypatch.setattr(pending, "pdf_to_markdown", lambda *_args: (_ for _ in ()).throw(OSError("disk full")))

    with pytest.raises(PendingImportError):
        import_pending_pdf(company, "news-1", source)

    assert source.read_bytes() == original
    assert list_pending(company) == [item()]
    assert list(company.rglob("*.pdf")) == []
    assert list((company / "annual-reports").rglob("*.md")) == []
    assert not (company / ".filingforge_index.json").exists()


def test_index_failure_rolls_back_seen_state_files_and_pending_removal(tmp_path, monkeypatch):
    import engine.pending as pending
    company = tmp_path / "library" / "KFINTECH"
    upsert_pending(company, item())
    source = tmp_path / "report.pdf"
    source.write_bytes(make_pdf())
    monkeypatch.setattr(pending, "build_index", lambda *_args: (_ for _ in ()).throw(OSError("disk full")))

    with pytest.raises(PendingImportError):
        import_pending_pdf(company, "news-1", source)

    assert list_pending(company) == [item()]
    assert list(company.rglob("*.pdf")) == []
    seen = company / ".filingforge_index.json"
    assert not seen.exists() or "news-1" not in json.loads(seen.read_text())


def test_unknown_pending_id_does_not_touch_source_or_library(tmp_path):
    company = tmp_path / "library" / "KFINTECH"
    upsert_pending(company, item())
    source = tmp_path / "report.pdf"
    original = make_pdf()
    source.write_bytes(original)

    with pytest.raises(PendingImportError, match="no longer pending"):
        import_pending_pdf(company, "missing", source)

    assert source.read_bytes() == original
    assert list(company.rglob("*.pdf")) == []


def test_seen_filing_prunes_stale_pending_and_cannot_be_manually_overwritten(tmp_path):
    company = tmp_path / "library" / "KFINTECH"
    pending = item()
    upsert_pending(company, pending)
    filing = Filing(
        news_id=pending.news_id, date=pending.date, headline=pending.headline,
        attachment=pending.bse_url, folder=pending.folder, category=pending.category,
    )
    record_seen(company, filing)
    source = tmp_path / "replacement.pdf"
    source.write_bytes(make_pdf())

    assert list_pending(company) == []
    with pytest.raises(PendingImportError, match="no longer pending"):
        import_pending_pdf(company, pending.news_id, source)


def test_existing_destination_is_never_overwritten_by_assisted_import(tmp_path):
    company = tmp_path / "library" / "KFINTECH"
    upsert_pending(company, item())
    destination = (
        company / "annual-reports" / "2026" /
        "2026-07-28_Annual_Report_FY_2025-26__news-1.pdf"
    )
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"%PDF-existing-correct-document")
    source = tmp_path / "replacement.pdf"
    source.write_bytes(make_pdf())

    with pytest.raises(PendingImportError, match="already exists"):
        import_pending_pdf(company, "news-1", source)

    assert destination.read_bytes() == b"%PDF-existing-correct-document"
    assert list_pending(company) == [item()]


def test_interrupted_commit_rolls_forward_on_next_pending_read(tmp_path):
    company = tmp_path / "library" / "KFINTECH"
    upsert_pending(company, item())
    destination = (
        company / "annual-reports" / "2026" /
        "2026-07-28_Annual_Report_FY_2025-26__news-1.pdf"
    )
    destination.parent.mkdir(parents=True)
    destination.write_bytes(make_pdf())
    md_destination = destination.with_suffix(".md")
    md_stage = md_destination.with_name(md_destination.name + ".part")
    md_stage.write_text("# recovered markdown\n", encoding="utf-8")
    marker = company / ".filingforge_import_txn.json"
    marker.write_text(json.dumps({
        "version": 1,
        "news_id": "news-1",
        "pdf_rel": destination.relative_to(company).as_posix(),
        "md_rel": md_destination.relative_to(company).as_posix(),
    }), encoding="utf-8")

    assert list_pending(company) == []
    assert md_destination.read_text(encoding="utf-8") == "# recovered markdown\n"
    assert json.loads((company / ".filingforge_index.json").read_text()) == ["news-1"]
    assert not marker.exists()
    assert destination.name in (company / "INDEX.md").read_text(encoding="utf-8")


def test_process_interruption_after_pdf_commit_is_recovered(tmp_path, monkeypatch):
    import engine.pending as pending_module

    company = tmp_path / "library" / "KFINTECH"
    upsert_pending(company, item())
    source = tmp_path / "report.pdf"
    source.write_bytes(make_pdf())
    real_replace = pending_module.os.replace
    interrupted = False

    def interrupt_after_pdf(source_path, destination_path):
        nonlocal interrupted
        real_replace(source_path, destination_path)
        if str(destination_path).endswith(".pdf") and not interrupted:
            interrupted = True
            raise KeyboardInterrupt("simulated process termination")

    monkeypatch.setattr(pending_module.os, "replace", interrupt_after_pdf)
    with pytest.raises(KeyboardInterrupt, match="simulated process termination"):
        import_pending_pdf(company, "news-1", source)

    monkeypatch.setattr(pending_module.os, "replace", real_replace)
    assert list_pending(company) == []
    destination = next(company.rglob("*.pdf"))
    assert destination.with_suffix(".md").exists()
    assert json.loads((company / ".filingforge_index.json").read_text()) == ["news-1"]
