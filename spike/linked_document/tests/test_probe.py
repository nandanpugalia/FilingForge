from importlib import import_module

from engine.models import Filing


def record(
    *,
    company: str,
    folder: str,
    reviewed_label: str,
    detected: bool,
    resolution_status: str = "substantive",
    page_count: int = 10,
) -> dict:
    return {
        "company": company,
        "folder": folder,
        "reviewed_label": reviewed_label,
        "detected": detected,
        "resolution_status": resolution_status,
        "page_count": page_count,
    }


def passing_records() -> list[dict]:
    companies = ["KFin Technologies", "HDFC Bank", "Maruti Suzuki", "Alpha", "Beta"]
    folders = ["annual-reports", "concalls", "investor-ppts"]
    cases = [
        record(
            company=companies[index % len(companies)],
            folder=folders[index % len(folders)],
            reviewed_label="cover",
            detected=True,
            resolution_status="resolved" if index < 12 else "unresolved",
            page_count=2,
        )
        for index in range(15)
    ]
    controls = [
        record(
            company=companies[index % len(companies)],
            folder=folders[index % len(folders)],
            reviewed_label="control",
            detected=False,
            page_count=2 if index < 10 else 12,
        )
        for index in range(30)
    ]
    return cases + controls


def test_uses_exactly_the_four_existing_curated_categories():
    probe = import_module("spike.linked_document.probe")

    specs = probe.category_specs()

    assert {spec.folder for spec in specs} == {"annual-reports", "concalls", "investor-ppts", "quarterly"}


def test_fixed_registry_contains_45_diverse_companies():
    probe = import_module("spike.linked_document.probe")

    companies = probe.load_companies()

    assert len(companies) == 45
    assert {company["scrip_code"] for company in companies} >= {"543720", "532500", "500180"}


def test_deduplicates_filings_by_bse_news_id():
    probe = import_module("spike.linked_document.probe")
    duplicate_a = Filing("same", "2026-01-01", "A", "a.pdf", "concalls", "Concall Transcripts")
    duplicate_b = Filing("same", "2026-01-02", "B", "b.pdf", "concalls", "Concall Transcripts")
    distinct = Filing("other", "2026-01-03", "C", "c.pdf", "quarterly", "Financial Results")

    assert probe.deduplicate_filings([duplicate_a, duplicate_b, distinct]) == [duplicate_a, distinct]


def test_control_sampling_keeps_genuine_short_documents_first():
    probe = import_module("spike.linked_document.probe")
    records = [
        {"news_id": "long", "detected": False, "page_count": 20},
        {"news_id": "short", "detected": False, "page_count": 2},
        {"news_id": "cover", "detected": True, "page_count": 2},
    ]

    assert [item["news_id"] for item in probe.select_controls(records, 2)] == ["short", "long"]


def test_gate_passes_only_when_every_requirement_is_satisfied():
    probe = import_module("spike.linked_document.probe")

    metrics = probe.compute_gate(
        passing_records(),
        adapter_hosts={"www.marutisuzuki.com"},
        normal_path_requests=0,
        minimum_cover_letters=15,
        minimum_companies=5,
        minimum_categories=3,
        minimum_controls=30,
    )

    assert metrics["verdict"] == "PASS"
    assert metrics["detection_recall"] == 1.0
    assert metrics["false_positives"] == 0
    assert metrics["resolution_rate"] == 0.8


def test_any_false_positive_fails_the_gate():
    probe = import_module("spike.linked_document.probe")
    records = passing_records()
    next(item for item in records if item["reviewed_label"] == "control")["detected"] = True

    metrics = probe.compute_gate(
        records,
        adapter_hosts={"www.marutisuzuki.com"},
        normal_path_requests=0,
        minimum_cover_letters=15,
        minimum_companies=5,
        minimum_categories=3,
        minimum_controls=30,
    )

    assert metrics["verdict"] == "FAIL"
    assert metrics["false_positives"] == 1


def test_unreviewed_or_small_corpus_is_reported_as_insufficient():
    probe = import_module("spike.linked_document.probe")

    metrics = probe.compute_gate(
        passing_records()[:10],
        adapter_hosts=set(),
        normal_path_requests=0,
        minimum_cover_letters=15,
        minimum_companies=5,
        minimum_categories=3,
        minimum_controls=30,
    )

    assert metrics["verdict"] == "INSUFFICIENT CORPUS"
