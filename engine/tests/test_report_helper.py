"""The report helper — a single app-managed file at the library root that holds the
locked FilingForge report visual template (Direction-C). Every skill references it, so
the visual layer is free + centrally upgradable and premium skills carry only logic."""
from pathlib import Path
from engine.report_helper import write_report_helper, HELPER_NAME


def test_writes_helper_to_library_root(tmp_path):
    path = write_report_helper(tmp_path)
    assert path == tmp_path / HELPER_NAME
    assert path.exists()


def test_helper_name_is_underscore_prefixed_markdown(tmp_path):
    # leading underscore sorts it to the top and signals "app-managed, not a company"
    assert HELPER_NAME.startswith("_")
    assert HELPER_NAME.endswith(".md")


def test_helper_contains_locked_direction_c_visuals(tmp_path):
    text = write_report_helper(tmp_path).read_text(encoding="utf-8")
    # the locked palette
    assert "#ff6a3d" in text          # ember accent
    assert "#faf6ec" in text          # paper
    # Direction-C signatures: dark header + ember divider + moat grid + KDK table
    assert "pg-header" in text and "ember-rule" in text
    assert "moat-grid" in text
    assert "Key Findings" in text
    # the FilingForge footer that spreads the product
    assert "filingforge.pages.dev" in text


def test_helper_is_self_contained_offline(tmp_path):
    text = write_report_helper(tmp_path).read_text(encoding="utf-8")
    # one file, zero deps: no EXTERNAL resource loads (the footer link to the site is fine —
    # it's a link, not a fetched asset). Catch the real antipatterns: loaded fonts/scripts/css.
    assert "fonts.googleapis" not in text and "fonts.gstatic" not in text
    assert 'src="http' not in text            # no external <script>/<img>
    assert 'href="https://cdn' not in text    # no CDN stylesheet
    assert "@import" not in text              # no imported external stylesheet


def test_helper_is_idempotent(tmp_path):
    first = write_report_helper(tmp_path).read_text(encoding="utf-8")
    second = write_report_helper(tmp_path).read_text(encoding="utf-8")
    assert first == second


def test_helper_overwrites_stale_version(tmp_path):
    # the app owns this file — a stale/edited copy must be replaced on next write
    (tmp_path / HELPER_NAME).write_text("OLD STALE TEMPLATE", encoding="utf-8")
    text = write_report_helper(tmp_path).read_text(encoding="utf-8")
    assert "OLD STALE TEMPLATE" not in text
    assert "moat-grid" in text


def test_helper_has_v2_markers(tmp_path):
    text = write_report_helper(tmp_path).read_text(encoding="utf-8")
    for marker in ("pg-header", "ember-rule", "Key Findings", "moat-grid",
                   "data-rev", "infer", 'id="ctx"', 'id="trend"'):
        assert marker in text, marker
    # graceful chart: instructions tell the AI to omit the chart if data is missing
    low = text.lower()
    assert "omit the chart" in low or "if the data isn't available" in low or "if the data isn’t available" in low
