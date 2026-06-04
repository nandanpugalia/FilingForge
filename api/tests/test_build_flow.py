import time


def _fake_work_factory(monkeypatch):
    """Replace api.routes.run_build with a fast fake that emits 2 events then returns counts."""
    import api.routes as routes
    def fake_run_build(scrip_code, ticker, dest, kinds, years):
        def work(on_progress):
            on_progress({"stage": "download", "current": 1, "total": 2, "message": "a", "percent": 50})
            on_progress({"stage": "download", "current": 2, "total": 2, "message": "b", "percent": 100})
            return {"downloaded": 2, "skipped": 0, "failed": 0}
        return work
    monkeypatch.setattr(routes, "run_build", fake_run_build)


def _poll(client, job_id, status, timeout=2.0):
    end = time.time() + timeout
    while time.time() < end:
        r = client.get(f"/build/{job_id}")
        if r.json()["status"] == status:
            return r.json()
        time.sleep(0.02)
    raise AssertionError(f"job {job_id} never reached {status}")


def test_build_starts_and_returns_job_id(client, monkeypatch):
    _fake_work_factory(monkeypatch)
    r = client.post("/build", json={"scrip_code": "532790", "ticker": "TANLA", "dest": "/tmp/x"})
    assert r.status_code == 202
    assert r.json()["job_id"]


def test_build_completes_with_result_counts(client, monkeypatch):
    _fake_work_factory(monkeypatch)
    job_id = client.post("/build", json={"scrip_code": "532790", "ticker": "TANLA",
                                         "dest": "/tmp/x"}).json()["job_id"]
    done = _poll(client, job_id, "done")
    assert done["result"] == {"downloaded": 2, "skipped": 0, "failed": 0}
    assert done["error"] is None


def test_status_unknown_job_is_404(client):
    r = client.get("/build/deadbeef")
    assert r.status_code == 404
    assert "user_message" in r.json()


def test_build_rejects_unknown_kind(client):
    r = client.post("/build", json={"scrip_code": "1", "ticker": "T", "dest": "/tmp/x",
                                    "kinds": ["bogus"]})
    assert r.status_code == 422


import json as _json


def test_sse_streams_progress_then_end(client, monkeypatch):
    _fake_work_factory(monkeypatch)
    job_id = client.post("/build", json={"scrip_code": "532790", "ticker": "TANLA",
                                         "dest": "/tmp/x"}).json()["job_id"]
    with client.stream("GET", f"/build/{job_id}/events") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        payloads, ended = [], False
        for line in resp.iter_lines():
            if not line:
                continue
            if line.startswith("event: end"):
                ended = True
                break
            if line.startswith("data: "):
                payloads.append(_json.loads(line[len("data: "):]))
    currents = [p["current"] for p in payloads if "current" in p]
    assert currents == [1, 2]
    assert ended


def test_sse_unknown_job_is_404(client):
    r = client.get("/build/nope/events")
    assert r.status_code == 404
