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


@pytest.mark.skipif(sys.platform.startswith("win"), reason="Windows uses os.startfile, not subprocess")
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


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="os.startfile is Windows-only")
def test_open_folder_uses_startfile_on_windows(tmp_path, monkeypatch):
    calls = {}
    monkeypatch.setattr(osutil.os, "startfile", lambda p: calls.setdefault("path", p), raising=False)
    open_folder(str(tmp_path))
    assert calls["path"] == str(tmp_path)


def test_open_folder_expands_tilde(tmp_path, monkeypatch):
    # The UI sends "~/..." paths; open_folder must expand ~ before validating/opening.
    monkeypatch.setenv("USERPROFILE", str(tmp_path))   # Windows home
    monkeypatch.setenv("HOME", str(tmp_path))           # macOS/Linux home
    (tmp_path / "lib").mkdir()
    opened = {}
    if sys.platform.startswith("win"):
        monkeypatch.setattr(osutil.os, "startfile", lambda p: opened.setdefault("p", p), raising=False)
    else:
        monkeypatch.setattr(osutil.subprocess, "run", lambda argv, **kw: opened.setdefault("p", argv[-1]))
    open_folder("~/lib")
    assert opened["p"] == str(tmp_path / "lib")


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
