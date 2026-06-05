"""Integration tests for the interactive web UI (server-rendered pages)."""


def test_home_page_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"FlightDeck" in resp.data


def test_home_lists_products(client, product):
    resp = client.get("/")
    assert b"Destroyer" in resp.data


def test_home_search_filters_products(client, product):
    # A non-matching query should not show the product
    resp = client.get("/?q=zzzzz")
    assert b"Destroyer" not in resp.data


def test_privacy_page_loads(client):
    resp = client.get("/privacy")
    assert resp.status_code == 200


def test_security_headers_present(client):
    resp = client.get("/")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert "Content-Security-Policy" in resp.headers


def test_csp_allows_external_https_product_images(client):
    # Scanned discs hotlink images from approved external shops over HTTPS.
    csp = client.get("/").headers["Content-Security-Policy"]
    img_src = next(part for part in csp.split(";") if part.strip().startswith("img-src"))
    assert "https:" in img_src


def test_logged_in_user_can_create_product(client, user):
    client.post("/auth/login", data={"username": "tester", "password": "password123"})
    resp = client.post(
        "/products/new",
        data={"name": "Wraith", "category": "Disc", "speed": 11, "glide": 5, "turn": -1, "fade": 3},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Wraith" in resp.data
