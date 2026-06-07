def test_skills_endpoint_lists_imported(client, monkeypatch):
    import api.routes as routes
    monkeypatch.setattr(routes, "list_imported_skills",
                        lambda d: [{"id": "forensic", "name": "Forensic DD", "tier": "Premium",
                                    "desc": "x", "prompt": "body", "imported": True}])
    r = client.get("/skills")
    assert r.status_code == 200
    skills = r.json()["skills"]
    assert skills[0]["id"] == "forensic" and skills[0]["tier"] == "Premium"


def test_skills_import_copies_and_returns_skill(client, monkeypatch, tmp_path):
    import api.routes as routes
    captured = {}
    def fake_import(src, directory):
        captured["src"] = src
        return {"id": "bought", "name": "Bought Skill", "tier": "Premium",
                "desc": "", "prompt": "run it", "imported": True}
    monkeypatch.setattr(routes, "import_skill", fake_import)
    r = client.post("/skills/import", json={"path": str(tmp_path / "bought.md")})
    assert r.status_code == 200
    assert r.json()["skill"]["name"] == "Bought Skill"
    assert str(captured["src"]) == str(tmp_path / "bought.md")


def test_skills_import_rejects_bad_file_with_friendly_message(client, monkeypatch):
    import api.routes as routes
    from engine.errors import SkillImportError
    def boom(src, directory):
        raise SkillImportError(technical="nope", user_message="A skill is a Markdown (.md) file. That file isn’t one.")
    monkeypatch.setattr(routes, "import_skill", boom)
    r = client.post("/skills/import", json={"path": "/tmp/evil.txt"})
    assert r.status_code == 400
    assert "Markdown" in r.json()["user_message"]


def test_skills_install_writes_content_and_returns_skill(client, monkeypatch):
    import api.routes as routes
    captured = {}
    def fake_save(name, content, directory):
        captured.update(name=name, content=content)
        return {"id": "concall-decoder", "name": "Concall Decoder", "tier": "Premium",
                "desc": "", "prompt": "decode", "imported": True}
    monkeypatch.setattr(routes, "save_skill_content", fake_save)
    r = client.post("/skills/install", json={"name": "Concall Decoder", "content": "decode"})
    assert r.status_code == 200
    assert r.json()["skill"]["id"] == "concall-decoder"
    assert captured["name"] == "Concall Decoder" and captured["content"] == "decode"


def test_skills_install_rejects_bad_name_with_friendly_message(client, monkeypatch):
    import api.routes as routes
    from engine.errors import SkillImportError
    def boom(name, content, directory):
        raise SkillImportError(technical="bad", user_message="Couldn’t install that skill — its name is invalid.")
    monkeypatch.setattr(routes, "save_skill_content", boom)
    r = client.post("/skills/install", json={"name": "...", "content": "x"})
    assert r.status_code == 400
    assert "install" in r.json()["user_message"]
