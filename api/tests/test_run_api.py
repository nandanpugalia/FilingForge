"""The FROZEN sidecar entry (sidecar/run_api.py) is what actually ships inside the Tauri app.
The dev entry (api/server.py) is exercised by `python -m api`, but the packaged binary runs
run_api.main() — so this is the entry that MUST honor FF_PORT, or the dynamic-port feature is
dead in the real app even with every other test green (this regression shipped once)."""
import sidecar.run_api as run_api


def _capture(monkeypatch):
    captured = {}
    # don't actually start a server; just record what main() would bind
    monkeypatch.setattr(run_api.uvicorn, "run", lambda app, **kw: captured.update(kw))
    return captured


def test_run_api_binds_ff_port(monkeypatch):
    monkeypatch.setenv("FF_PORT", "8771")
    captured = _capture(monkeypatch)
    run_api.main()
    assert captured["port"] == 8771
    assert captured["host"] == "127.0.0.1"   # loopback only — the token gate depends on it


def test_run_api_defaults_to_8765_without_env(monkeypatch):
    monkeypatch.delenv("FF_PORT", raising=False)
    captured = _capture(monkeypatch)
    run_api.main()
    assert captured["port"] == 8765
    assert captured["host"] == "127.0.0.1"
