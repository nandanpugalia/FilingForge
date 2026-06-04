import pytest
from pydantic import ValidationError
from api.schemas import ResolveRequest, BuildRequest, CandidateOut, JobCreated, JobStatusOut


def test_resolve_request_requires_nonempty_company():
    assert ResolveRequest(company="TANLA").company == "TANLA"
    with pytest.raises(ValidationError):
        ResolveRequest(company="")


def test_build_request_defaults_and_kinds():
    r = BuildRequest(scrip_code="532790", ticker="TANLA", dest="/tmp/x")
    assert r.years == 5
    assert r.kinds == ["annual_report", "results", "investor_ppt", "concall"]


def test_build_request_rejects_unknown_kind():
    with pytest.raises(ValidationError):
        BuildRequest(scrip_code="532790", ticker="TANLA", dest="/tmp/x", kinds=["bogus"])


def test_candidate_out_shape():
    c = CandidateOut(scrip_code="532790", company="Tanla Platforms Ltd", is_primary=True)
    assert c.model_dump() == {"scrip_code": "532790", "company": "Tanla Platforms Ltd",
                              "is_primary": True}


def test_job_status_out_carries_progress_and_result():
    s = JobStatusOut(job_id="j1", status="running",
                     progress={"stage": "download", "current": 2, "total": 9,
                               "message": "Downloading…", "percent": 22})
    assert s.status == "running" and s.progress["percent"] == 22
    assert s.result is None and s.error is None
