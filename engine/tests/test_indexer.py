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
    # relative link still embeds the category folder (now year-nested too)
    assert "annual-reports/" in text and "corp-actions/" in text


def test_index_groups_by_year_subsections_descending(tmp_path):
    root = company_dir(tmp_path, "TANLA")
    # two years within the same category
    save_filing(root, _f("q-24", "2024-05-01", "Q4 FY24", "quarterly", "Financial Results"), b"%PDF-x")
    save_filing(root, _f("q-25a", "2025-01-15", "Q3 FY25", "quarterly", "Financial Results"), b"%PDF-x")
    save_filing(root, _f("q-25b", "2025-05-01", "Q4 FY25", "quarterly", "Financial Results"), b"%PDF-x")
    text = build_index(root, "TANLA").read_text()
    assert "## Quarterly" in text
    assert "### 2025" in text and "### 2024" in text
    # 2025 section comes before 2024 (descending years)
    assert text.index("### 2025") < text.index("### 2024")
    # within 2025, the later date (Q4 FY25, 2025-05-01) sorts before the earlier
    assert text.index("Q4 FY25") < text.index("Q3 FY25")
    # link path is relative to company dir and includes the year folder
    assert "quarterly/2025/" in text and "quarterly/2024/" in text


def test_index_year_groups_flat_legacy_library_without_migration(tmp_path):
    # Simulate an existing FLAT library: category/file.pdf with NO year folder.
    root = company_dir(tmp_path, "SBIN")
    flat_cat = root / "annual-reports"
    flat_cat.mkdir(parents=True)
    (flat_cat / "2024-07-01_Annual_Report__leg1.pdf").write_bytes(b"%PDF-x")
    (flat_cat / "2023-07-01_Annual_Report__leg2.pdf").write_bytes(b"%PDF-x")
    text = build_index(root, "SBIN").read_text()
    assert "## Annual Reports" in text
    # grouped by year DERIVED FROM FILENAME even though files are flat on disk
    assert "### 2024" in text and "### 2023" in text
    assert text.index("### 2024") < text.index("### 2023")
    # files NOT moved: link path is the real flat path (no year folder inserted)
    assert "annual-reports/2024-07-01_Annual_Report__leg1.pdf" in text
    assert "annual-reports/2024/" not in text


def test_index_undated_group_when_filename_has_no_year(tmp_path):
    root = company_dir(tmp_path, "SBIN")
    cat = root / "press"
    cat.mkdir(parents=True)
    (cat / "notes__x.pdf").write_bytes(b"%PDF-x")
    text = build_index(root, "SBIN").read_text()
    assert "### Undated" in text


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


def test_read_library_counts_year_nested_pdfs(tmp_path):
    # year-nested layout from save_filing across two years in one category
    t = company_dir(tmp_path, "SBIN")
    save_filing(t, _f("q-24", "2024-05-01", "Q4", "quarterly", "Financial Results"), b"%PDF-x")
    save_filing(t, _f("q-25", "2025-05-01", "Q4", "quarterly", "Financial Results"), b"%PDF-x")
    save_filing(t, _f("ar-25", "2025-07-01", "AR", "annual-reports", "Annual Reports"), b"%PDF-x")
    build_index(t, "SBIN")
    lib = read_library(tmp_path)
    assert len(lib) == 1
    row = lib[0]
    assert row["ticker"] == "SBIN"
    # counts keyed by CATEGORY folder, summed across year subfolders
    assert row["counts"] == {"annual-reports": 1, "quarterly": 2}
    assert row["total"] == 3


def test_is_company_dir_detects_year_nested(tmp_path):
    from engine.indexer import _is_company_dir
    t = company_dir(tmp_path, "SBIN")
    save_filing(t, _f("q-25", "2025-05-01", "Q4", "quarterly", "Financial Results"), b"%PDF-x")
    # no INDEX.md yet — must still be detected as a company via year-nested pdf
    assert not (t / "INDEX.md").exists()
    assert _is_company_dir(t) is True
