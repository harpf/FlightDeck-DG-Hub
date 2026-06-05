"""Integration tests for the RESTful Web-API (headless, token-authenticated)."""


def test_health_is_public(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_products_requires_token(client, product):
    resp = client.get("/api/v1/products")
    assert resp.status_code == 401
    assert "error" in resp.get_json()


def test_products_rejects_malformed_token(client, product):
    resp = client.get("/api/v1/products", headers={"X-API-Token": "not-a-valid-token"})
    assert resp.status_code == 401


def test_products_list_with_token(client, product, api_token):
    resp = client.get("/api/v1/products", headers={"X-API-Token": api_token})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["count"] == 1
    assert data["products"][0]["name"] == "Destroyer"
    # list view omits reviews to keep the payload small
    assert "reviews" not in data["products"][0]


def test_products_filter_by_query(client, product, api_token):
    resp = client.get("/api/v1/products?q=destroyer", headers={"X-API-Token": api_token})
    assert resp.status_code == 200
    assert resp.get_json()["count"] == 1

    resp_none = client.get("/api/v1/products?q=zzzzz", headers={"X-API-Token": api_token})
    assert resp_none.get_json()["count"] == 0


def test_product_detail_with_token(client, product, api_token):
    resp = client.get(f"/api/v1/products/{product.id}", headers={"X-API-Token": api_token})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["name"] == "Destroyer"
    assert data["flight_numbers"]["speed"] == 12
    assert "reviews" in data


def test_product_detail_404(client, api_token):
    resp = client.get("/api/v1/products/9999", headers={"X-API-Token": api_token})
    assert resp.status_code == 404


def test_full_dump_with_token(client, product, api_token):
    resp = client.get("/api/v1/full", headers={"X-API-Token": api_token})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "products" in data and "source_requests" in data


def test_openapi_spec_served(client):
    resp = client.get("/api/openapi.json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["openapi"].startswith("3.")
    assert "/api/v1/products" in data["paths"]
    assert "ApiTokenAuth" in data["components"]["securitySchemes"]


def test_swagger_ui_page(client):
    resp = client.get("/api/docs")
    assert resp.status_code == 200
    assert b"swagger-ui" in resp.data


def test_deactivated_token_is_rejected(client, product, api_token, db):
    from app.models import ApiToken

    token_id = int(api_token.split(".", 1)[0])
    db.session.get(ApiToken, token_id).is_active = False
    db.session.commit()

    resp = client.get("/api/v1/products", headers={"X-API-Token": api_token})
    assert resp.status_code == 401
