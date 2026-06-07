"""Imported Skills — the revenue seam.

A Skill is just a Markdown file. The app reads two shelves: built-in skills bundled
in the UI, and *imported* skills living in ``~/.filingforge/skills/``. Premium packs
(sold later as a paid .md download) arrive through the very same import path — drop the
file in this folder and it shows up like any other skill. Because the folder lives in
the user's home, not the app bundle, imported skills survive reinstalls and updates with
no licence server, no DRM, no phone-home. Ownership = possession of the file.

Optional YAML-ish frontmatter (``name`` / ``tier`` / ``desc``) drives how the skill is
labelled; with no frontmatter we derive a sensible name from the filename and default to
the Free tier, so a plain community .md imports cleanly.
"""
from __future__ import annotations
import re
import shutil
from pathlib import Path

from .errors import SkillImportError

# A real FilingForge skill declares itself in its frontmatter: `filingforge_skill: <version>`.
# This is a FORMAT gate, not an origin lock — anyone can author a conforming skill (open
# ecosystem). It stops a user importing a random .md that would never work and making the
# app look broken. (Cryptographic signing + a "verified" badge for official skills is a
# later, premium-launch step — see docs/REVENUE.md.)
MANIFEST_KEY = "filingforge_skill"


def skills_dir() -> Path:
    """The user's imported-skills folder: ``~/.filingforge/skills/`` (not auto-created)."""
    return Path("~/.filingforge/skills").expanduser()


def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return (frontmatter dict, body). Frontmatter is a leading ``---`` ... ``---`` block of
    simple ``key: value`` lines. No YAML dependency — we only need flat string fields."""
    meta: dict[str, str] = {}
    if not text.startswith("---"):
        return meta, text
    lines = text.splitlines()
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return meta, text
    for line in lines[1:end]:
        key, sep, val = line.partition(":")
        if sep:
            meta[key.strip().lower()] = val.strip()
    body = "\n".join(lines[end + 1:]).lstrip("\n")
    return meta, body


def _slugify(name: str) -> str:
    """A safe, lowercase, hyphenated filename stem — no path separators, no traversal.
    Empty/unsluggable names raise so we never write a stray or escaping file."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    if not slug:
        raise SkillImportError(
            technical=f"unsluggable skill name: {name!r}",
            user_message="Couldn’t install that skill — its name is invalid.",
        )
    return slug


def _titleize(stem: str) -> str:
    words = stem.replace("-", " ").replace("_", " ").strip()
    return words[:1].upper() + words[1:] if words else stem


def _skill_from_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    meta, body = _split_frontmatter(text)
    tier = meta.get("tier", "Free")
    if tier not in ("Free", "Premium"):
        tier = "Free"
    return {
        "id": path.stem,
        "name": meta.get("name") or _titleize(path.stem),
        "tier": tier,
        "desc": meta.get("desc", ""),
        "prompt": body if (meta or body) else text,
        "imported": True,
    }


def list_imported_skills(directory: Path) -> list[dict]:
    """Every ``*.md`` in ``directory`` as a skill dict, sorted by filename. Missing dir → []."""
    directory = Path(directory).expanduser()
    if not directory.exists():
        return []
    return [_skill_from_file(p) for p in sorted(directory.glob("*.md"))]


def import_skill(src: Path, directory: Path) -> dict:
    """Copy a ``.md`` skill file into ``directory`` (created if needed) and return the skill.
    Rejects non-markdown or missing files with a user-facing message."""
    src = Path(src).expanduser()
    if not src.is_file():
        raise SkillImportError(
            technical=f"skill source not found: {src}",
            user_message="Couldn't find that file. Pick the skill’s .md file and try again.",
        )
    if src.suffix.lower() != ".md":
        raise SkillImportError(
            technical=f"not a markdown skill: {src.name}",
            user_message="A skill is a Markdown (.md) file. That file isn’t one.",
        )
    meta, _ = _split_frontmatter(src.read_text(encoding="utf-8", errors="replace"))
    if MANIFEST_KEY not in meta:
        raise SkillImportError(
            technical=f"missing {MANIFEST_KEY} manifest: {src.name}",
            user_message="This isn’t a FilingForge skill. A skill file starts with a "
                         "FilingForge manifest — see the “Write a skill” guide.",
        )
    directory = Path(directory).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    dest = directory / src.name
    shutil.copyfile(src, dest)
    return _skill_from_file(dest)


def save_skill_content(name: str, content: str, directory: Path) -> dict:
    """Install a skill that arrived as md TEXT (a paid pack downloaded from the Worker, not a
    file the user picked). Writes ``content`` to ``directory/<safe-slug>.md`` and returns the
    skill exactly as ``list_imported_skills`` would, so it shows up like any imported skill.

    The name is slugified to a safe filename (no path separators / traversal). Unlike
    ``import_skill`` we don't re-require the manifest here — the content came from our own
    Worker, not an arbitrary user file — but it is parsed identically once on disk."""
    slug = _slugify(name)
    directory = Path(directory).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    dest = directory / f"{slug}.md"
    dest.write_text(content, encoding="utf-8")
    return _skill_from_file(dest)
