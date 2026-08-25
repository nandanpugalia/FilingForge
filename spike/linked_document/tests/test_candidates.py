from datetime import date
from importlib import import_module

from spike.linked_document.models import Candidate, DocumentContext


def context(
    folder: str = "annual-reports",
    headline: str = "Annual Report FY 2025-26",
) -> DocumentContext:
    return DocumentContext(
        company="Example Limited",
        folder=folder,
        filing_date=date(2026, 7, 28),
        headline=headline,
        source_url="https://www.bseindia.com/example.pdf",
    )


def test_parses_relative_pdf_links_and_excludes_duplicates_and_assets():
    candidates = import_module("spike.linked_document.candidates")
    html = b"""
        <a href="/reports/FY2025-26.pdf">Annual Report FY 2025-26</a>
        <a href="/reports/FY2025-26.pdf#page=1">Duplicate</a>
        <a href="javascript:void(0)">Script</a>
        <a href="https://investor.example.com/logo.png">Logo</a>
        <a href="mailto:investor@example.com">Email</a>
    """

    parsed = candidates.parse_html_candidates(html, "https://investor.example.com/annual-reports/")

    assert parsed == (
        Candidate(
            url="https://investor.example.com/reports/FY2025-26.pdf",
            label="Annual Report FY 2025-26",
            source="html",
        ),
    )


def test_parses_onclick_pdf_with_nearby_quarter_and_transcript_label():
    candidates = import_module("spike.linked_document.candidates")
    html = b"""
      <div class="row">
        <span>Q1</span><i>L&amp;T Earnings Call Transcript Q1FY27</i>
        <a href="#" onclick="return fnDownloadpdf('https://investor.example.com/Q1FY27-Transcript.pdf');">
          Download
        </a>
        <a href="#" onclick="return fnDownloadpdf('https://investor.example.com/Q1FY27-Audio.mp3');">
          Audio
        </a>
      </div>
    """

    parsed = candidates.parse_html_candidates(html, "https://investor.example.com/transcripts")

    assert len(parsed) == 1
    assert parsed[0].url == "https://investor.example.com/Q1FY27-Transcript.pdf"
    assert "Earnings Call Transcript Q1FY27" in parsed[0].label


def test_ordinary_href_does_not_inherit_unrelated_nearby_text():
    candidates = import_module("spike.linked_document.candidates")
    html = b"""
      <div>Annual Report FY 2025-26</div>
      <a href="/reports/Annual_Report_FY_2024-25.pdf">Download PDF</a>
    """

    parsed = candidates.parse_html_candidates(html, "https://investor.example.com/")

    assert parsed[0].label == "Download PDF"


def test_infers_equivalent_financial_year_tokens():
    candidates = import_module("spike.linked_document.candidates")

    tokens = candidates.infer_period_tokens(context(), "Financial Year 2025-2026")

    assert {"fy202526", "fy26", "202526", "20252026"} <= tokens


def test_maps_december_quarter_end_to_q3_of_next_financial_year():
    candidates = import_module("spike.linked_document.candidates")
    ctx = context("investor-ppts", "Investor Presentation")

    tokens = candidates.infer_period_tokens(ctx, "for the quarter ended December 31, 2025")

    assert {"q3fy26", "q3fy202526"} <= tokens


def test_maps_march_quarter_end_to_q4_of_same_financial_year():
    candidates = import_module("spike.linked_document.candidates")
    ctx = context("concalls", "Earnings Call Transcript")

    tokens = candidates.infer_period_tokens(ctx, "for the quarter and year ended March 31, 2026")

    assert {"q4fy26", "q4fy202526"} <= tokens


def test_maps_indian_day_first_quarter_end_to_fiscal_quarter():
    candidates = import_module("spike.linked_document.candidates")
    ctx = context("concalls", "Earnings Call Transcript")

    tokens = candidates.infer_period_tokens(ctx, "for the quarter ended on 30th September 2025")

    assert {"q2fy26", "q2fy202526"} <= tokens


def test_infers_ocr_spaced_short_fy_with_explicit_quarter():
    candidates = import_module("spike.linked_document.candidates")
    ctx = context("concalls", "Transcript of Q1 / FY2 7 Earnings Call")

    tokens = candidates.infer_period_tokens(ctx, "Q1 / FY2 7 Earnings Call transcript")

    assert {"fy27", "fy202627", "q1fy27", "q1fy202627"} <= tokens


def test_selects_unique_candidate_with_matching_type_and_period():
    candidates = import_module("spike.linked_document.candidates")
    choices = (
        Candidate("https://example.com/ar-fy24-25.pdf", "Annual Report FY 2024-25", "html"),
        Candidate("https://example.com/ar-fy25-26.pdf", "Annual Report FY 2025-26", "html"),
        Candidate("https://example.com/q3fy26.pdf", "Q3FY26 Earnings Presentation", "html"),
    )

    selected = candidates.select_unique_candidate(context(), "", choices)

    assert selected == choices[1]
    score = candidates.score_candidate(context(), "", choices[1])
    assert score.type_score == 6
    assert score.period_score == 5


def test_concall_transcript_beats_same_quarter_invite_and_audio():
    candidates = import_module("spike.linked_document.candidates")
    ctx = context("concalls", "Earnings Call Transcript")
    cover = "Transcript for the quarter ended on 30th September 2025"
    choices = (
        Candidate("https://example.com/Q2FY26-transcript.pdf", "Q2 FY26 Earnings Call Transcript", "adapter"),
        Candidate("https://example.com/Q2FY26-invite.pdf", "Q2 FY26 Conference Call Invite", "adapter"),
        Candidate("https://example.com/Q2FY26-audio.mp3", "Q2 FY26 Conference Call Audio", "adapter"),
    )

    assert candidates.select_unique_candidate(ctx, cover, choices) == choices[0]


def test_annual_report_matches_standalone_ar_filename_despite_june_letter_date():
    candidates = import_module("spike.linked_document.candidates")
    ctx = context("annual-reports", "Annual Report")
    cover = "Letter dated June 29, 2026. Annual Report for Financial Year 2025-26."
    choices = (
        Candidate("https://example.com/Company_AR_2025-26.pdf", "Download PDF", "html"),
        Candidate("https://example.com/Annual-Report-FY-2024-25.pdf", "Download PDF", "html"),
    )

    assert candidates.select_unique_candidate(ctx, cover, choices) == choices[0]


def test_does_not_match_incompatible_document_type():
    candidates = import_module("spike.linked_document.candidates")
    presentation = Candidate(
        "https://example.com/q3fy26.pdf",
        "Q3FY26 Earnings Presentation",
        "html",
    )

    assert candidates.select_unique_candidate(context(), "", (presentation,)) is None


def test_tied_best_candidates_are_ambiguous():
    candidates = import_module("spike.linked_document.candidates")
    choices = (
        Candidate("https://a.example/ar.pdf", "Annual Report FY 2025-26", "html"),
        Candidate("https://b.example/ar.pdf", "Annual Report FY 2025-26", "html"),
    )

    assert candidates.select_unique_candidate(context(), "", choices) is None


def test_below_threshold_candidate_is_not_selected():
    candidates = import_module("spike.linked_document.candidates")
    undated = Candidate("https://example.com/annual-report.pdf", "Annual Report", "html")

    assert candidates.select_unique_candidate(context(), "", (undated,)) is None
