"""Integration tests for the authenticated write API (admin-scoped tokens)."""
from app.models import Product, ProductReview, SourceRequest


def _h(token):
    return {"X-API-Token": token}


# --- authorization scope ---------------------------------------------------

def test_write_requires_token(client):
    resp = client.post("/api/v1/products", json={"name": "X"})
    assert resp.status_code == 401


def test_write_rejected_for_read_only_token(client, api_token):
    resp = client.post("/api/v1/products", json={"name": "X"}, headers=_h(api_token))
    assert resp.status_code == 403
    assert "error" in resp.get_json()


# --- products CRUD ---------------------------------------------------------

def test_create_product(client, admin_api_token):
    body = {
        "name": "Wraith",
        "manufacturer": "Innova",
        "disc_type": "Distance Driver",
        "speed": 11, "glide": 5, "turn": -1, "fade": 3,
        "image_url": "https://shop.example/wraith.jpg",
    }
    resp = client.post("/api/v1/products", json=body, headers=_h(admin_api_token))
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["name"] == "Wraith"
    assert data["category"] == "Disc"  # default
    assert data["flight_numbers"]["speed"] == 11
    assert Product.query.count() == 1


def test_create_product_requires_name(client, admin_api_token):
    resp = client.post("/api/v1/products", json={"manufacturer": "Innova"}, headers=_h(admin_api_token))
    assert resp.status_code == 400


def test_create_product_rejects_non_numeric_flight_value(client, admin_api_token):
    # Guards the flight-chart SVG sink: a string in speed must never be stored.
    payload = {"name": "Pwn", "speed": "</text></svg><img src=x onerror=alert(1)>"}
    resp = client.post("/api/v1/products", json=payload, headers=_h(admin_api_token))
    assert resp.status_code == 400
    assert Product.query.count() == 0


def test_update_product_rejects_non_numeric_flight_value(client, admin_api_token, product):
    resp = client.patch(
        f"/api/v1/products/{product.id}",
        json={"turn": "not-a-number"},
        headers=_h(admin_api_token),
    )
    assert resp.status_code == 400


def test_update_product(client, admin_api_token, product):
    resp = client.patch(
        f"/api/v1/products/{product.id}",
        json={"fade": 4, "plastic_type": "Star"},
        headers=_h(admin_api_token),
    )
    assert resp.status_code == 200
    assert resp.get_json()["flight_numbers"]["fade"] == 4
    from app.extensions import db
    refreshed = db.session.get(Product, product.id)
    assert refreshed.fade == 4 and refreshed.plastic_type == "Star"


def test_update_missing_product_is_404(client, admin_api_token):
    resp = client.patch("/api/v1/products/999", json={"fade": 4}, headers=_h(admin_api_token))
    assert resp.status_code == 404


def test_delete_product(client, admin_api_token, product):
    resp = client.delete(f"/api/v1/products/{product.id}", headers=_h(admin_api_token))
    assert resp.status_code == 204
    assert Product.query.count() == 0


def test_delete_missing_product_is_404(client, admin_api_token):
    resp = client.delete("/api/v1/products/999", headers=_h(admin_api_token))
    assert resp.status_code == 404


# --- sources ---------------------------------------------------------------

def test_create_source(client, admin_api_token):
    resp = client.post(
        "/api/v1/sources",
        json={"source_url": "https://shop.example/kat/discs/", "note": "neu"},
        headers=_h(admin_api_token),
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["source_url"] == "https://shop.example/kat/discs/"
    assert data["status"] == "open"
    assert SourceRequest.query.count() == 1


def test_update_source_status(client, admin_api_token, admin):
    src = SourceRequest(source_url="https://shop.example/x/", status="open", requested_by_id=admin.id)
    from app.extensions import db
    db.session.add(src)
    db.session.commit()
    resp = client.patch(f"/api/v1/sources/{src.id}", json={"status": "approved"}, headers=_h(admin_api_token))
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "approved"


def test_scan_source_via_api(client, admin_api_token, admin, monkeypatch):
    from app.extensions import db
    from app.scanner import ScannedProduct
    src = SourceRequest(source_url="https://shop.example/kat/discs/", status="approved", requested_by_id=admin.id)
    db.session.add(src)
    db.session.commit()
    monkeypatch.setattr("app.services.is_scraping_allowed", lambda url: True)
    monkeypatch.setattr(
        "app.services.scan_products_from_url",
        lambda url: [ScannedProduct("Buzzz", "mid", "Discraft", "https://shop.example/pr/buzzz/", speed=5)],
    )
    resp = client.post(f"/api/v1/sources/{src.id}/scan", headers=_h(admin_api_token))
    assert resp.status_code == 200
    assert resp.get_json() == {"found": 1, "created": 1, "duplicates": 0}
    assert Product.query.filter_by(name="Buzzz").count() == 1


def test_scan_non_approved_source_is_409(client, admin_api_token, admin):
    from app.extensions import db
    src = SourceRequest(source_url="https://shop.example/x/", status="open", requested_by_id=admin.id)
    db.session.add(src)
    db.session.commit()
    resp = client.post(f"/api/v1/sources/{src.id}/scan", headers=_h(admin_api_token))
    assert resp.status_code == 409


# --- reviews ---------------------------------------------------------------

def test_create_review_via_api(client, admin_api_token, product):
    resp = client.post(
        f"/api/v1/products/{product.id}/reviews",
        json={"rating": 5, "comment": "Stark"},
        headers=_h(admin_api_token),
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["rating"] == 5 and data["comment"] == "Stark"
    assert ProductReview.query.count() == 1


def test_create_review_rejects_bad_rating(client, admin_api_token, product):
    resp = client.post(
        f"/api/v1/products/{product.id}/reviews",
        json={"rating": 9},
        headers=_h(admin_api_token),
    )
    assert resp.status_code == 400


# --- OpenAPI documentation -------------------------------------------------

def test_openapi_documents_write_endpoints(client):
    spec = client.get("/api/openapi.json").get_json()
    paths = spec["paths"]
    assert "post" in paths["/api/v1/products"]
    assert "patch" in paths["/api/v1/products/{id}"]
    assert "delete" in paths["/api/v1/products/{id}"]
    assert "post" in paths["/api/v1/sources"]
    assert "post" in paths["/api/v1/sources/{id}/scan"]
    assert "post" in paths["/api/v1/products/{id}/reviews"]
    assert "ProductInput" in spec["components"]["schemas"]
