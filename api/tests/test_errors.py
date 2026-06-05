def test_validation_error_is_422(client):
    r = client.post("/build", json={"ticker": "T", "dest": "/tmp/x"})  # missing scrip_code
    assert r.status_code == 422


def test_unknown_route_404_shape(client):
    r = client.get("/does-not-exist")
    assert r.status_code == 404
    assert "user_message" in r.json()   # our HTTPException handler renders friendly


def test_server_binds_loopback_constant():
    from api.server import HOST
    assert HOST == "127.0.0.1"          # never 0.0.0.0 — local-first guarantee
