def test_library_endpoint_lists_companies(client, tmp_path, monkeypatch):
    import api.routes as routes
    monkeypatch.setattr(routes, "read_library",
                        lambda root: [{"ticker": "TANLA", "total": 2,
                                       "counts": {"annual-reports": 1, "quarterly": 1}}])
    r = client.get("/library", params={"root": str(tmp_path)})
    assert r.status_code == 200
    assert r.json()["companies"][0]["ticker"] == "TANLA"


def test_library_endpoint_requires_root(client):
    r = client.get("/library")
    assert r.status_code == 422
