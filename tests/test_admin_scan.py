"""Tests for the admin source-scan endpoint feedback and error handling."""
from app.models import Product, SourceRequest
from app.scanner import ScannedProduct


def _login_admin(client):
    client.post("/auth/login", data={"username": "admin", "password": "adminpass123"})


def _approved_source(db, admin):
    src = SourceRequest(
        source_url="https://shop.example/kat/discs/",
        status="approved",
        requested_by_id=admin.id,
    )
    db.session.add(src)
    db.session.commit()
    return src


def test_scan_reports_found_new_and_duplicate_counts(client, db, admin, monkeypatch):
    src = _approved_source(db, admin)
    monkeypatch.setattr("app.routes.is_scraping_allowed", lambda url: True)
    monkeypatch.setattr(
        "app.routes.scan_products_from_url",
        lambda url: [
            ScannedProduct("Axiom Balance", "mid", "Axiom", "https://shop.example/pr/a/"),
            ScannedProduct("Axiom Envy", "putter", "Axiom", "https://shop.example/pr/b/"),
        ],
    )
    _login_admin(client)
    resp = client.post(f"/admin/sources/{src.id}/scan", follow_redirects=True)
    assert resp.status_code == 200
    assert "2 gefunden".encode() in resp.data
    assert "2 neu".encode() in resp.data
    assert Product.query.count() == 2


def test_scan_reports_zero_when_no_structured_data(client, db, admin, monkeypatch):
    src = _approved_source(db, admin)
    monkeypatch.setattr("app.routes.is_scraping_allowed", lambda url: True)
    monkeypatch.setattr("app.routes.scan_products_from_url", lambda url: [])
    _login_admin(client)
    resp = client.post(f"/admin/sources/{src.id}/scan", follow_redirects=True)
    assert resp.status_code == 200
    assert "Keine strukturierten Produktdaten".encode() in resp.data
    assert Product.query.count() == 0


def test_scan_handles_fetch_error_without_500(client, db, admin, monkeypatch):
    src = _approved_source(db, admin)
    monkeypatch.setattr("app.routes.is_scraping_allowed", lambda url: True)

    def boom(url):
        raise OSError("connection refused")

    monkeypatch.setattr("app.routes.scan_products_from_url", boom)
    _login_admin(client)
    resp = client.post(f"/admin/sources/{src.id}/scan", follow_redirects=True)
    assert resp.status_code == 200
    assert "fehlgeschlagen".encode() in resp.data


def test_scan_counts_existing_products_as_duplicates(client, db, admin, monkeypatch):
    src = _approved_source(db, admin)
    db.session.add(Product(name="Axiom Balance", manufacturer="Axiom", category="Disc"))
    db.session.commit()
    monkeypatch.setattr("app.routes.is_scraping_allowed", lambda url: True)
    monkeypatch.setattr(
        "app.routes.scan_products_from_url",
        lambda url: [ScannedProduct("Axiom Balance", "mid", "Axiom", "https://shop.example/pr/a/")],
    )
    _login_admin(client)
    resp = client.post(f"/admin/sources/{src.id}/scan", follow_redirects=True)
    assert resp.status_code == 200
    assert "0 neu".encode() in resp.data
    assert "1 bereits vorhanden".encode() in resp.data
    assert Product.query.count() == 1
