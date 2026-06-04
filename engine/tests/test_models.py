from engine.models import Candidate, Filing, FilingType, LibraryResult


def test_filing_type_maps_to_bse_category_subcategory():
    assert FilingType.ANNUAL_REPORT.bse == ("Others", "Reg. 34 (1) Annual Report")
    assert FilingType.RESULTS.bse == ("Result", "Financial Results")
    assert FilingType.INVESTOR_PPT.bse == ("Company Update", "Investor Presentation")
    assert FilingType.CONCALL.bse == ("Company Update", "Earnings Call Transcript")


def test_filing_type_folder_names_are_clean():
    assert FilingType.ANNUAL_REPORT.folder == "annual-reports"
    assert FilingType.RESULTS.folder == "quarterly"
    assert FilingType.INVESTOR_PPT.folder == "investor-ppts"
    assert FilingType.CONCALL.folder == "concalls"


def test_candidate_primary_flag():
    c = Candidate(scrip_code="532790", company="Tanla Platforms Ltd", is_primary=True)
    assert c.scrip_code == "532790" and c.is_primary


def test_library_result_counts():
    r = LibraryResult(downloaded=["a", "b"], skipped=["c"], failed=["d"])
    assert r.total_attempted == 4
    assert r.ok is True   # ok = at least one downloaded and folder intact


def test_library_result_ok_false_when_nothing_downloaded():
    r = LibraryResult(downloaded=[], skipped=[], failed=["x"])
    assert r.ok is False
