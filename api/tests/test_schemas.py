import pytest
from pydantic import ValidationError
from api.schemas import ResolveRequest, BuildRequest, CandidateOut, JobStatusOut, LibraryItem


def test_resolve_request_requires_nonempty_company():
    assert ResolveRequest(company="TANLA").company == "TANLA"
    with pytest.raises(ValidationError):
        ResolveRequest(company="")


def test_build_request_defaults_to_everything_one_year():
    r = BuildRequest(scrip_code="532790", ticker="TANLA", dest="/tmp/x")
    assert r.years == 1 and r.everything is True and r.categories == []


def test_build_request_accepts_curated_category_keys():
    r = BuildRequest(scrip_code="532790", ticker="TANLA", dest="/tmp/x",
                     everything=False, categories=["annual_report", "results"])
    assert r.categories == ["annual_report", "results"]


def test_build_request_rejects_unknown_category_key():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        BuildRequest(scrip_code="1", ticker="T", dest="/tmp/x",
                     everything=False, categories=["bogus"])


def test_candidate_out_includes_isin():
    c = CandidateOut(scrip_code="532790", company="Tanla Platforms Ltd", is_primary=True,
                     isin="INE483C01032")
    assert c.model_dump()["isin"] == "INE483C01032"


def test_candidate_out_includes_symbol():
    c = CandidateOut(scrip_code="532790", company="Tanla Platforms Ltd", is_primary=True,
                     isin="INE483C01032", symbol="TANLA")
    assert c.model_dump()["symbol"] == "TANLA"


def test_library_item_shape():
    it = LibraryItem(ticker="TANLA", total=2, counts={"annual-reports": 1, "quarterly": 1})
    assert it.total == 2 and it.counts["quarterly"] == 1


def test_job_status_out_carries_progress_and_result():
    s = JobStatusOut(job_id="j1", status="running",
                     progress={"stage": "download", "current": 2, "total": 9,
                               "message": "Downloading…", "percent": 22})
    assert s.status == "running" and s.progress["percent"] == 22
    assert s.result is None and s.error is None
