from pathlib import Path
from engine.organiser import (
    company_dir, save_filing, save_markdown, clean_partials,
    already_have, filing_label, load_seen, record_seen,
)
from engine.models import Filing


def _f(news_id="ar-1", att="ar1.pdf"):
    return Filing(news_id=news_id, date="2025-07-01", headline="Annual Report 2024-25",
                  attachment=att, folder="annual-reports", category="Annual Reports")


def test_company_dir_uses_clean_ticker(tmp_path):
    d = company_dir(tmp_path, "TANLA")
    assert d == tmp_path / "TANLA"


def test_save_filing_writes_into_type_folder_with_readable_name(tmp_path):
    root = company_dir(tmp_path, "TANLA")
    path = save_filing(root, _f(), b"%PDF-1.7 data")
    # NEW year-nested layout: <category>/<YYYY>/<file>.pdf
    assert path.parent == root / "annual-reports" / "2025"
    assert path.suffix == ".pdf"
    assert "2025-07-01" in path.name
    assert path.read_bytes().startswith(b"%PDF-")


def test_supported_filing_uses_semantic_filename_not_bse_boilerplate(tmp_path):
    root = company_dir(tmp_path, "KFINTECH")
    filing = Filing(
        news_id="news-1",
        date="2026-02-05",
        headline=("Please find attached Investor Presentation and Factsheet on performance "
                  "for the quarter and nine months ended December 31, 2025"),
        attachment="notice.pdf",
        folder="investor-ppts",
        category="Investor Presentations",
    )

    path = save_filing(root, filing, b"%PDF-1.7 data")

    assert "Investor_presentation" in path.name
    assert "2025-12-31" in path.name
    assert "Please_find_attached" not in path.name
    assert path.name.endswith("__news-1.pdf")


def test_supported_filing_without_period_uses_type_and_filing_date(tmp_path):
    root = company_dir(tmp_path, "KFINTECH")
    filing = Filing(
        news_id="news-2",
        date="2026-02-05",
        headline="Please find attached the transcript",
        attachment="notice.pdf",
        folder="concalls",
        category="Concall Transcripts",
    )

    path = save_filing(root, filing, b"%PDF-1.7 data")

    assert path.name == "2026-02-05_Concall_transcript__news-2.pdf"


def test_progress_label_does_not_guess_fiscal_year_without_fy_evidence():
    filing = Filing(
        news_id="results-1",
        date="2025-05-08",
        headline="Financial Results for Q1 2025",
        attachment="results.pdf",
        folder="quarterly",
        category="Financial Results",
    )

    assert filing_label(filing) == "Financial results — filed 8 May 2025"


def test_save_filing_nests_pdf_and_md_under_year(tmp_path):
    root = company_dir(tmp_path, "TANLA")
    path = save_filing(root, _f(news_id="ar-9"), b"%PDF-x")
    # pdf is under <category>/<YYYY>/
    assert path.parent == root / "annual-reports" / "2025"
    assert path.exists()
    # the .md sibling written next to it lands in the same year folder
    md = path.with_suffix(".md")
    md.write_text("dummy")
    assert md.parent == root / "annual-reports" / "2025"


def test_save_filing_undated_when_date_not_a_year(tmp_path):
    root = company_dir(tmp_path, "TANLA")
    f = Filing(news_id="x-1", date="bad-date", headline="No date",
               attachment="x.pdf", folder="press", category="Press")
    path = save_filing(root, f, b"%PDF-x")
    assert path.parent == root / "press" / "undated"


def test_dedup_roundtrip(tmp_path):
    root = company_dir(tmp_path, "TANLA")
    assert already_have(root, _f()) is False
    record_seen(root, _f())
    assert already_have(root, _f()) is True
    assert "ar-1" in load_seen(root)


def test_seen_persists_across_calls(tmp_path):
    root = company_dir(tmp_path, "TANLA")
    record_seen(root, _f(news_id="x"))
    record_seen(root, _f(news_id="y"))
    assert load_seen(root) == {"x", "y"}


# ── Atomic writes: an interrupted download must never leave a half-file the index picks up ──

def test_save_filing_leaves_no_part_remnant(tmp_path):
    root = company_dir(tmp_path, "TANLA")
    path = save_filing(root, _f(), b"%PDF-1.7 full")
    # success → final file is complete and NO *.part remnant remains
    assert path.read_bytes() == b"%PDF-1.7 full"
    assert list(path.parent.glob("*.part")) == []


def test_save_markdown_is_atomic_sibling(tmp_path):
    root = company_dir(tmp_path, "TANLA")
    pdf = save_filing(root, _f(news_id="m-1"), b"%PDF-x")
    md = save_markdown(pdf, "# clean markdown")
    assert md == pdf.with_suffix(".md")
    assert md.read_text(encoding="utf-8") == "# clean markdown"
    assert list(md.parent.glob("*.part")) == []


def test_partial_part_files_are_invisible_to_pdf_glob(tmp_path):
    # A leftover *.part (e.g. process killed mid-write) must NOT be seen as a real filing:
    # the indexer scans rglob("*.pdf"), so .part is excluded by construction. Lock it.
    root = company_dir(tmp_path, "TANLA")
    folder = root / "annual-reports" / "2025"
    folder.mkdir(parents=True)
    (folder / "2025-07-01_x__n1.pdf.part").write_bytes(b"%PDF-half")   # interrupted
    (folder / "2025-07-01_y__n2.pdf").write_bytes(b"%PDF-full")        # complete
    pdfs = list(root.rglob("*.pdf"))
    assert len(pdfs) == 1 and pdfs[0].name.endswith("n2.pdf")


def test_library_config_roundtrip_and_legacy_returns_none(tmp_path):
    from engine.organiser import save_library_config, load_library_config
    root = company_dir(tmp_path, "TANLA")
    # a legacy v0.1.6 library (or brand-new) has no config yet
    assert load_library_config(root) is None
    save_library_config(root, ["annual_report", "results"], everything=False)
    cfg = load_library_config(root)
    assert cfg["categories"] == ["annual_report", "results"]
    assert cfg["everything"] is False


def test_clean_partials_removes_stray_part_files(tmp_path):
    root = company_dir(tmp_path, "TANLA")
    folder = root / "annual-reports" / "2025"
    folder.mkdir(parents=True)
    stray = folder / "2025-07-01_x__n1.pdf.part"
    stray.write_bytes(b"%PDF-half")
    keep = folder / "2025-07-01_y__n2.pdf"
    keep.write_bytes(b"%PDF-full")
    n = clean_partials(root)
    assert n == 1
    assert not stray.exists() and keep.exists()
