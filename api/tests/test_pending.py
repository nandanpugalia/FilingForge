from io import BytesIO

from pypdf import PdfWriter

from engine.models import PendingDocument
from engine.organiser import company_dir
from engine.pending import list_pending, upsert_pending


def pending_item() -> PendingDocument:
    return PendingDocument(
        news_id="news-1",
        date="2026-07-28",
        headline="Annual Report FY 2025-26",
        folder="annual-reports",
        category="Annual Reports",
        expected_type="Annual report",
        expected_period="FY 2025-26",
        bse_url="https://www.bseindia.com/xml-data/corpfiling/AttachHis/notice.pdf",
        issuer_url="https://investor.example.com/annual-reports/",
        reason="could not select one unique replacement PDF",
    )


def substantive_pdf() -> bytes:
    writer = PdfWriter()
    for _ in range(4):
        writer.add_blank_page(width=612, height=792)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_lists_pending_items_for_sanitized_company_path(client, tmp_path):
    company = company_dir(tmp_path, "../KFINTECH")
    upsert_pending(company, pending_item())

    response = client.get("/pending", params={"root": str(tmp_path), "ticker": "../KFINTECH"})

    assert response.status_code == 200
    assert response.json()["pending"][0]["news_id"] == "news-1"
    assert company == tmp_path / "KFINTECH"


def test_missing_company_has_empty_pending_list(client, tmp_path):
    response = client.get("/pending", params={"root": str(tmp_path), "ticker": "MISSING"})

    assert response.status_code == 200
    assert response.json() == {"pending": []}


def test_import_completes_pending_slot_and_returns_destination(client, tmp_path):
    company = company_dir(tmp_path / "library", "KFINTECH")
    upsert_pending(company, pending_item())
    source = tmp_path / "Downloads" / "report.pdf"
    source.parent.mkdir()
    source.write_bytes(substantive_pdf())

    response = client.post("/pending/import", json={
        "root": str(tmp_path / "library"),
        "ticker": "KFINTECH",
        "news_id": "news-1",
        "path": str(source),
    })

    assert response.status_code == 200
    body = response.json()
    assert body["news_id"] == "news-1"
    assert body["destination"].endswith("__news-1.pdf")
    assert body["pending"] == []
    assert source.exists()
    assert list_pending(company) == []


def test_import_expands_tilde_source_path(client, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    root = tmp_path / "library"
    company = company_dir(root, "KFINTECH")
    upsert_pending(company, pending_item())
    source = tmp_path / "report.pdf"
    source.write_bytes(substantive_pdf())

    response = client.post("/pending/import", json={
        "root": str(root),
        "ticker": "KFINTECH",
        "news_id": "news-1",
        "path": "~/report.pdf",
    })

    assert response.status_code == 200


def test_invalid_pdf_returns_friendly_client_error_and_keeps_pending(client, tmp_path):
    root = tmp_path / "library"
    company = company_dir(root, "KFINTECH")
    upsert_pending(company, pending_item())
    source = tmp_path / "bad.pdf"
    source.write_bytes(b"not a pdf")

    response = client.post("/pending/import", json={
        "root": str(root),
        "ticker": "KFINTECH",
        "news_id": "news-1",
        "path": str(source),
    })

    assert response.status_code == 400
    assert "user_message" in response.json()
    assert list_pending(company) == [pending_item()]


def test_unknown_pending_id_returns_friendly_client_error(client, tmp_path):
    source = tmp_path / "report.pdf"
    source.write_bytes(substantive_pdf())

    response = client.post("/pending/import", json={
        "root": str(tmp_path / "library"),
        "ticker": "KFINTECH",
        "news_id": "missing",
        "path": str(source),
    })

    assert response.status_code == 400
    assert "no longer pending" in response.json()["user_message"]

