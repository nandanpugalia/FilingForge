"""Tests for the MCP tool layer — pure functions over a library on disk.

Kept free of the MCP SDK so the behaviour is testable on its own; `server.py` is
a thin adapter that registers these.

Library layout the engine writes, and these read:

    <root>/<TICKER>/<category-folder>/<YYYY>/<YYYY-MM-DD>_<Headline>__<id>.pdf
                                            + the .md sibling
    <root>/<TICKER>/INDEX.md
    <root>/INDEX.md
"""
import pytest

from mcp_server.tools import (
    get_index,
    list_companies,
    read_filing,
    search_filings,
)


@pytest.fixture
def library(tmp_path):
    def add(ticker, folder, year, name, md="# clean markdown\n"):
        d = tmp_path / ticker / folder / year
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{name}.pdf").write_bytes(b"%PDF-1.7")
        (d / f"{name}.md").write_text(md)

    add("ESCORTS", "annual-reports", "2013", "2013-02-22_Annual_Report_2012__AR-500495-2012",
        md="# Escorts Annual Report 2012\n\nTractor volumes fell 3%.\n")
    add("ESCORTS", "annual-reports", "2000", "2000-03-31_Annual_Report_2000__AR-500495-2000")
    add("ESCORTS", "quarterly", "2013", "2013-05-28_Q4_Results__res-1")
    add("VSTTILLERS", "annual-reports", "2013", "2013-06-10_Annual_Report_2013__AR-531266-2013")

    (tmp_path / "ESCORTS" / "INDEX.md").write_text("# ESCORTS\n\n3 filings\n")
    (tmp_path / "INDEX.md").write_text("# Library\n\n2 companies\n")
    return tmp_path


# ------------------------------------------------------------ list_companies

def test_lists_every_company_in_the_library(library):
    assert [c["ticker"] for c in list_companies(library)] == ["ESCORTS", "VSTTILLERS"]


def test_reports_how_many_filings_each_company_has(library):
    escorts = next(c for c in list_companies(library) if c["ticker"] == "ESCORTS")
    assert escorts["filings"] == 3


def test_reports_the_categories_present_for_a_company(library):
    escorts = next(c for c in list_companies(library) if c["ticker"] == "ESCORTS")
    assert escorts["categories"] == ["annual-reports", "quarterly"]


def test_an_empty_library_lists_nothing(tmp_path):
    assert list_companies(tmp_path) == []


def test_a_root_that_does_not_exist_lists_nothing(tmp_path):
    assert list_companies(tmp_path / "nope") == []


# ------------------------------------------------------------------ get_index

def test_returns_a_companys_index(library):
    assert "ESCORTS" in get_index(library, "ESCORTS")


def test_returns_the_master_index_when_no_company_is_named(library):
    assert "2 companies" in get_index(library)


def test_a_missing_index_reads_as_empty_rather_than_raising(library):
    assert get_index(library, "VSTTILLERS") == ""


# -------------------------------------------------------------- search_filings

def test_finds_filings_by_text_in_the_name(library):
    hits = search_filings(library, "annual report")
    assert len(hits) == 3


def test_search_is_case_insensitive(library):
    assert search_filings(library, "ANNUAL") == search_filings(library, "annual")


def test_narrows_by_company(library):
    hits = search_filings(library, "annual report", ticker="VSTTILLERS")
    assert [h["ticker"] for h in hits] == ["VSTTILLERS"]


def test_narrows_by_category(library):
    hits = search_filings(library, "", ticker="ESCORTS", category="quarterly")
    assert len(hits) == 1 and hits[0]["category"] == "quarterly"


def test_narrows_by_year(library):
    hits = search_filings(library, "", ticker="ESCORTS", year="2000")
    assert len(hits) == 1 and hits[0]["year"] == "2000"


def test_an_empty_query_returns_everything_in_scope(library):
    assert len(search_filings(library, "")) == 4


def test_respects_the_result_limit(library):
    assert len(search_filings(library, "", limit=2)) == 2


def test_returns_newest_first(library):
    dates = [h["date"] for h in search_filings(library, "annual report")]
    assert dates == sorted(dates, reverse=True)


def test_each_hit_carries_a_path_that_read_filing_accepts(library):
    hit = search_filings(library, "annual report", ticker="ESCORTS", year="2013")[0]
    assert "Tractor volumes" in read_filing(library, hit["path"])


# ---------------------------------------------------------------- read_filing

def test_reads_the_clean_markdown_not_the_pdf(library):
    path = "ESCORTS/annual-reports/2013/2013-02-22_Annual_Report_2012__AR-500495-2012.md"
    assert read_filing(library, path).startswith("# Escorts Annual Report 2012")


def test_a_pdf_path_is_served_as_its_markdown_sibling(library):
    path = "ESCORTS/annual-reports/2013/2013-02-22_Annual_Report_2012__AR-500495-2012.pdf"
    assert "Tractor volumes" in read_filing(library, path)


def test_refuses_to_escape_the_library_with_dot_dot(library):
    (library.parent / "secret.md").write_text("private")
    with pytest.raises(ValueError):
        read_filing(library, "../secret.md")


def test_refuses_a_nested_traversal(library):
    with pytest.raises(ValueError):
        read_filing(library, "ESCORTS/../../secret.md")


def test_refuses_an_absolute_path_outside_the_library(library):
    with pytest.raises(ValueError):
        read_filing(library, "/etc/hosts")


def test_a_missing_filing_raises_a_clear_error(library):
    with pytest.raises(FileNotFoundError):
        read_filing(library, "ESCORTS/annual-reports/2013/nope.md")
