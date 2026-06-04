from pathlib import Path
from engine.organiser import company_dir, save_filing
from engine.indexer import build_index, build_master_index
from engine.models import Filing


def _f(news_id, date, head, folder, category):
    return Filing(news_id=news_id, date=date, headline=head,
                  attachment=f"{news_id}.pdf", folder=folder, category=category)


def test_index_lists_every_saved_doc_grouped_by_real_folder(tmp_path):
    root = company_dir(tmp_path, "TANLA")
    save_filing(root, _f("ar-1", "2025-07-01", "Annual Report 2024-25", "annual-reports", "Annual Reports"), b"%PDF-x")
    save_filing(root, _f("d-1", "2026-04-24", "Dividend", "corp-actions", "Dividends & Corp Actions"), b"%PDF-x")
    text = build_index(root, "TANLA").read_text()
    assert "# TANLA" in text
    assert "Annual Reports" in text and "Corp Actions" in text
    assert "Annual Report 2024-25" in text and "2026-04-24" in text
    assert "annual-reports/" in text and "corp-actions/" in text


def test_index_is_idempotent(tmp_path):
    root = company_dir(tmp_path, "TANLA")
    save_filing(root, _f("ar-1", "2025-07-01", "AR", "annual-reports", "Annual Reports"), b"%PDF-x")
    build_index(root, "TANLA")
    first = (root / "INDEX.md").read_text()
    build_index(root, "TANLA")
    assert (root / "INDEX.md").read_text() == first


def test_master_index_lists_every_company_with_counts(tmp_path):
    t = company_dir(tmp_path, "TANLA")
    save_filing(t, _f("ar-1", "2025-07-01", "AR", "annual-reports", "Annual Reports"), b"%PDF-x")
    build_index(t, "TANLA")
    r = company_dir(tmp_path, "RELIANCE")
    save_filing(r, _f("res-1", "2026-01-01", "Q3", "quarterly", "Financial Results"), b"%PDF-x")
    save_filing(r, _f("res-2", "2026-04-01", "Q4", "quarterly", "Financial Results"), b"%PDF-x")
    build_index(r, "RELIANCE")
    path = build_master_index(tmp_path)
    text = path.read_text()
    assert path == tmp_path / "INDEX.md"
    assert "TANLA" in text and "RELIANCE" in text
    assert "1" in text and "2" in text
    assert "TANLA/INDEX.md" in text and "RELIANCE/INDEX.md" in text


def test_master_index_ignores_non_company_files(tmp_path):
    (tmp_path / "INDEX.md").write_text("# old")
    (tmp_path / "notes.txt").write_text("x")
    t = company_dir(tmp_path, "TANLA")
    save_filing(t, _f("ar-1", "2025-07-01", "AR", "annual-reports", "Annual Reports"), b"%PDF-x")
    text = build_master_index(tmp_path).read_text()
    assert "TANLA" in text and "notes" not in text


from engine.indexer import read_library


def test_read_library_returns_per_company_summaries(tmp_path):
    t = company_dir(tmp_path, "TANLA")
    save_filing(t, _f("ar-1", "2025-07-01", "AR", "annual-reports", "Annual Reports"), b"%PDF-x")
    save_filing(t, _f("res-1", "2026-01-01", "Q3", "quarterly", "Financial Results"), b"%PDF-x")
    build_index(t, "TANLA")
    lib = read_library(tmp_path)
    assert len(lib) == 1
    row = lib[0]
    assert row["ticker"] == "TANLA"
    assert row["total"] == 2
    assert row["counts"] == {"annual-reports": 1, "quarterly": 1}


def test_read_library_empty_when_no_companies(tmp_path):
    assert read_library(tmp_path) == []
