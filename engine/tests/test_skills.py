import pytest
from engine.skills import list_imported_skills, import_skill, skills_dir
from engine.errors import FilingForgeError


def test_skills_dir_is_under_home_filingforge(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows parity
    assert skills_dir() == tmp_path / ".filingforge" / "skills"


def test_list_returns_empty_when_dir_absent(tmp_path):
    assert list_imported_skills(tmp_path / "nope") == []


def test_list_parses_frontmatter(tmp_path):
    d = tmp_path / "skills"; d.mkdir()
    (d / "forensic.md").write_text(
        "---\nname: Forensic DD\ntier: Premium\ndesc: Balance-sheet forensics.\n---\nDo the forensics.\n",
        encoding="utf-8")
    skills = list_imported_skills(d)
    assert len(skills) == 1
    s = skills[0]
    assert s["id"] == "forensic" and s["name"] == "Forensic DD"
    assert s["tier"] == "Premium" and s["desc"] == "Balance-sheet forensics."
    assert s["prompt"].strip() == "Do the forensics."


def test_list_falls_back_to_filename_when_no_frontmatter(tmp_path):
    # A community .md with no frontmatter still imports cleanly: name from filename, Free by default.
    d = tmp_path / "skills"; d.mkdir()
    (d / "my-cool-skill.md").write_text("# A skill\nbody", encoding="utf-8")
    s = list_imported_skills(d)[0]
    assert s["name"] == "My cool skill" and s["tier"] == "Free"
    assert s["prompt"].startswith("# A skill")


def test_list_is_sorted_and_skips_non_md(tmp_path):
    d = tmp_path / "skills"; d.mkdir()
    (d / "b.md").write_text("---\nname: Bravo\n---\nx", encoding="utf-8")
    (d / "a.md").write_text("---\nname: Alpha\n---\ny", encoding="utf-8")
    (d / "notes.txt").write_text("ignore me", encoding="utf-8")
    names = [s["name"] for s in list_imported_skills(d)]
    assert names == ["Alpha", "Bravo"]


def test_import_copies_md_into_skills_dir_and_returns_it(tmp_path):
    src = tmp_path / "bought.md"
    src.write_text("---\nfilingforge_skill: 1\nname: Bought Skill\ntier: Premium\ndesc: Paid pack.\n---\nrun it",
                   encoding="utf-8")
    dest = tmp_path / "store"        # does not exist yet — import must create it
    s = import_skill(src, dest)
    assert (dest / "bought.md").exists()
    assert s["name"] == "Bought Skill" and s["tier"] == "Premium" and s["id"] == "bought"


def test_import_rejects_a_file_without_the_filingforge_manifest(tmp_path):
    # a random .md (even with some frontmatter) is NOT a FilingForge skill → don't mislead the user
    src = tmp_path / "random.md"
    src.write_text("---\nname: My Notes\n---\njust some notes", encoding="utf-8")
    with pytest.raises(FilingForgeError) as ei:
        import_skill(src, tmp_path / "store")
    assert "FilingForge skill" in ei.value.user_message
    assert not (tmp_path / "store").exists()   # nothing copied in


def test_import_rejects_a_plain_markdown_with_no_frontmatter(tmp_path):
    src = tmp_path / "plain.md"
    src.write_text("# Hello\nnot a skill", encoding="utf-8")
    with pytest.raises(FilingForgeError):
        import_skill(src, tmp_path / "store")


def test_import_rejects_non_markdown(tmp_path):
    src = tmp_path / "evil.txt"; src.write_text("nope", encoding="utf-8")
    with pytest.raises(FilingForgeError):
        import_skill(src, tmp_path / "store")


def test_import_rejects_missing_file(tmp_path):
    with pytest.raises(FilingForgeError):
        import_skill(tmp_path / "ghost.md", tmp_path / "store")
