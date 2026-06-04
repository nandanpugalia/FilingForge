from engine.models import (
    Candidate, Filing, CategorySpec, CURATED, CURATED_BY_KEY, slug, LibraryResult,
)


def test_slug_lowercases_and_hyphenates():
    assert slug("Company Update") == "company-update"
    assert slug("Corp. Action") == "corp-action"
    assert slug("AGM/EGM") == "agm-egm"


def test_curated_has_nine_specs_with_unique_keys_and_folders():
    assert len(CURATED) == 9
    assert len({c.key for c in CURATED}) == 9
    assert len({c.folder for c in CURATED}) == 9
    assert CURATED_BY_KEY["annual_report"].folder == "annual-reports"


def test_exact_spec_matches_category_and_subcategory():
    ar = CURATED_BY_KEY["annual_report"]
    assert ar.matches("Others", "Reg. 34 (1) Annual Report") is True
    assert ar.matches("Others", "Something else") is False
    assert ar.matches("Result", "Reg. 34 (1) Annual Report") is False


def test_wildcard_spec_matches_whole_category():
    corp = CURATED_BY_KEY["corp_actions"]
    assert corp.subcategory is None
    assert corp.matches("Corp. Action", "Dividend") is True
    assert corp.matches("Corp. Action", "Record Date") is True
    assert corp.matches("Result", "Dividend") is False


def test_filing_carries_folder_and_category_strings():
    f = Filing(news_id="n1", date="2025-07-01", headline="AR 2025",
               attachment="a.pdf", folder="annual-reports", category="Annual Reports")
    assert f.folder == "annual-reports" and f.category == "Annual Reports"


def test_candidate_has_optional_isin():
    assert Candidate("532790", "Tanla Platforms Ltd", True).isin is None
    assert Candidate("532790", "Tanla", True, isin="INE483C01032").isin == "INE483C01032"


def test_candidate_has_optional_symbol():
    assert Candidate("532790", "Tanla", True).symbol is None
    assert Candidate("532790", "Tanla", True, isin="INE483C01032", symbol="TANLA").symbol == "TANLA"


def test_library_result_unchanged():
    r = LibraryResult(downloaded=["a"], skipped=[], failed=["b"])
    assert r.total_attempted == 2 and r.ok is True


def test_slug_neutralizes_windows_reserved_names():
    assert slug("CON") == "con-cat"
    assert slug("LPT1") == "lpt1-cat"
    assert slug("nul") == "nul-cat"
    assert slug("Company Update") == "company-update"   # normal names unaffected
