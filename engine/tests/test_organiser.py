from pathlib import Path
from engine.organiser import (
    company_dir, save_filing, already_have, load_seen, record_seen,
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
