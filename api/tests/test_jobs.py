import threading
import time
import pytest
from api.jobs import JobManager, JOB_DONE_SENTINEL, run_build
from engine.errors import BSEUnavailableError
from engine.models import LibraryResult, PendingDocument


def _wait(job, status, timeout=2.0):
    end = time.time() + timeout
    while time.time() < end:
        if job.status == status:
            return
        time.sleep(0.01)
    raise AssertionError(f"job never reached {status!r}; stuck at {job.status!r}")


def test_successful_job_runs_work_emits_events_and_finishes():
    mgr = JobManager()
    job = mgr.create()

    def work(on_progress):
        on_progress({"stage": "download", "current": 1, "total": 2, "message": "a", "percent": 50})
        on_progress({"stage": "download", "current": 2, "total": 2, "message": "b", "percent": 100})
        return {"downloaded": 2, "skipped": 0, "failed": 0}

    mgr.start(job, work)
    _wait(job, "done")
    assert job.result == {"downloaded": 2, "skipped": 0, "failed": 0}
    drained = []
    while True:
        ev = job.events.get(timeout=1)
        if ev is JOB_DONE_SENTINEL:
            break
        drained.append(ev)
    assert [e["current"] for e in drained] == [1, 2]


def test_failing_job_captures_friendly_error_and_sentinel():
    mgr = JobManager()
    job = mgr.create()

    def work(on_progress):
        raise BSEUnavailableError("connect timeout")

    mgr.start(job, work)
    _wait(job, "error")
    assert "BSE" in job.error and "try again" in job.error.lower()
    assert job.result is None
    assert job.events.get(timeout=1) is JOB_DONE_SENTINEL


def test_unexpected_error_is_generic_friendly_not_raw():
    mgr = JobManager()
    job = mgr.create()

    def work(on_progress):
        raise RuntimeError("boom internal detail")

    mgr.start(job, work)
    _wait(job, "error")
    assert "boom internal detail" not in job.error
    assert job.error


def test_cancel_sets_event_and_marks_status_cancelled():
    mgr = JobManager()
    job = mgr.create()
    started = threading.Event()

    def work(on_progress):
        started.set()
        while not job.cancel_event.is_set():   # the engine's should_cancel polls this
            time.sleep(0.01)
        return {"downloaded": 3, "skipped": 0, "failed": 0, "cancelled": True}

    mgr.start(job, work)
    assert started.wait(2)
    assert mgr.cancel(job.id) is True
    _wait(job, "cancelled")
    assert job.result["cancelled"] is True


def test_cancel_unknown_job_returns_false():
    assert JobManager().cancel("nope") is False


def test_get_returns_none_for_unknown_job():
    assert JobManager().get("nope") is None


def test_create_assigns_unique_ids():
    mgr = JobManager()
    assert mgr.create().id != mgr.create().id


def test_run_build_serializes_pending_documents(monkeypatch, tmp_path):
    import engine.bse_client as bse
    import engine.library as library
    pending = PendingDocument(
        news_id="news-1", date="2026-07-28", headline="Annual Report FY 2025-26",
        folder="annual-reports", category="Annual Reports", expected_type="Annual report",
        expected_period="FY 2025-26", bse_url="https://www.bseindia.com/notice.pdf",
        issuer_url="https://investor.example.com/reports/", reason="ambiguous",
    )
    monkeypatch.setattr(bse, "BSEClient", lambda: type("Client", (), {"close": lambda self: None})())
    monkeypatch.setattr(
        library, "build_library",
        lambda *_args, **_kwargs: LibraryResult(downloaded=["done"], pending=[pending]),
    )

    result = run_build("1", "KFINTECH", str(tmp_path), False, ["annual_report"], 2)(lambda _event: None)

    assert result["downloaded"] == 1
    assert result["pending"] == [{
        "news_id": "news-1", "date": "2026-07-28", "headline": "Annual Report FY 2025-26",
        "folder": "annual-reports", "category": "Annual Reports", "expected_type": "Annual report",
        "expected_period": "FY 2025-26", "bse_url": "https://www.bseindia.com/notice.pdf",
        "issuer_url": "https://investor.example.com/reports/", "reason": "ambiguous",
    }]
