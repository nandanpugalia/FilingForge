from engine.organiser import company_dir, save_filing
from engine.indexer import build_index
from engine.models import Filing, FilingType


def _f(news_id, date, head, kind):
    return Filing(news_id=news_id, date=date, headline=head,
                  attachment=f"{news_id}.pdf", kind=kind)


def test_index_lists_every_saved_doc_grouped_by_type(tmp_path):
    root = company_dir(tmp_path, "TANLA")
    save_filing(root, _f("ar-1", "2025-07-01", "Annual Report 2024-25", FilingType.ANNUAL_REPORT), b"%PDF-x")
    save_filing(root, _f("res-1", "2026-04-24", "Q4 Results", FilingType.RESULTS), b"%PDF-x")
    path = build_index(root, "TANLA")
    text = path.read_text()
    assert path.name == "INDEX.md"
    assert "# TANLA" in text
    assert "Annual Reports" in text and "Quarterly" in text
    assert "Annual Report 2024-25" in text
    assert "2026-04-24" in text
    assert "annual-reports/" in text          # relative link the AI/user can follow


def test_index_is_rebuilt_not_appended(tmp_path):
    root = company_dir(tmp_path, "TANLA")
    save_filing(root, _f("ar-1", "2025-07-01", "AR", FilingType.ANNUAL_REPORT), b"%PDF-x")
    build_index(root, "TANLA")
    first = (root / "INDEX.md").read_text()
    build_index(root, "TANLA")               # idempotent — same contents, no duplication
    assert (root / "INDEX.md").read_text() == first
