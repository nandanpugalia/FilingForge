import sys
import pytest
from api.osutil import open_folder
from api import osutil


def test_open_folder_rejects_missing_path(tmp_path):
    missing = tmp_path / "nope"
    with pytest.raises(FileNotFoundError):
        open_folder(str(missing))


def test_open_folder_rejects_file_not_dir(tmp_path):
    f = tmp_path / "a.txt"; f.write_text("x")
    with pytest.raises(NotADirectoryError):
        open_folder(str(f))


def test_open_folder_invokes_launcher_without_shell(tmp_path, monkeypatch):
    calls = {}
    def fake_run(argv, **kw):
        calls["argv"] = argv
        calls["shell"] = kw.get("shell", False)
    monkeypatch.setattr(osutil.subprocess, "run", fake_run)
    open_folder(str(tmp_path))
    assert isinstance(calls["argv"], list)
    assert calls["shell"] is False
    assert str(tmp_path) in calls["argv"]


def test_route_open_folder_ok(client, tmp_path, monkeypatch):
    import api.routes as routes
    monkeypatch.setattr(routes, "open_folder", lambda p: None)
    r = client.post("/open-folder", json={"path": str(tmp_path)})
    assert r.status_code == 200 and r.json()["ok"] is True


def test_route_open_folder_missing_is_404(client, tmp_path, monkeypatch):
    import api.routes as routes
    def boom(p):
        raise FileNotFoundError(p)
    monkeypatch.setattr(routes, "open_folder", boom)
    r = client.post("/open-folder", json={"path": str(tmp_path / "x")})
    assert r.status_code == 404
    assert "user_message" in r.json()
