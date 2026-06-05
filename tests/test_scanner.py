from app.scanner import build_robots_url, is_scraping_allowed, scan_products_from_url


class DummyResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return b'<script type="application/ld+json">{"@type":"Product","name":"Test Disc","description":"Desc","url":"https://x"}</script>'


class DummyRobotParser:
    def set_url(self, _url):
        return None

    def read(self):
        return None

    def can_fetch(self, _user_agent, _url):
        return False


def test_scan_products_from_url(monkeypatch):
    monkeypatch.setattr("app.scanner.urlopen", lambda *args, **kwargs: DummyResponse())
    products = scan_products_from_url("https://example.org")
    assert len(products) == 1
    assert products[0].name == "Test Disc"


def test_build_robots_url():
    assert build_robots_url("https://example.org/products/discs") == "https://example.org/robots.txt"


def test_is_scraping_allowed_respects_parser(monkeypatch):
    monkeypatch.setattr("app.scanner.RobotFileParser", DummyRobotParser)
    assert is_scraping_allowed("https://example.org/products") is False


# --- Improved scanner: pure parsing helpers --------------------------------

from app.scanner import (  # noqa: E402
    clean_name,
    extract_next_page_url,
    extract_product_links,
    extract_products_from_html,
)


def test_clean_name_trims_to_first_segment():
    assert clean_name("Axiom Balance | Midrange | discgolf4you") == "Axiom Balance"
    assert clean_name("  Lone Name  ") == "Lone Name"


def test_extract_products_finds_product_nested_in_graph():
    html = """
    <script type="application/ld+json">
    {"@context":"https://schema.org","@graph":[
      {"@type":"Organization","name":"Shop"},
      {"@type":"Product","name":"Axiom Balance | Midrange | shop",
       "description":"A midrange","brand":{"@type":"Brand","name":"Axiom"},
       "url":"/pr/axiom-balance/"}
    ]}
    </script>
    """
    products = extract_products_from_html(html, "https://shop.example/kat/discs/")
    assert len(products) == 1
    assert products[0].name == "Axiom Balance"
    assert products[0].manufacturer == "Axiom"
    assert products[0].product_url == "https://shop.example/pr/axiom-balance/"


def test_extract_products_handles_type_as_list():
    html = (
        '<script type="application/ld+json">'
        '{"@type":["Product","IndividualProduct"],"name":"Defy"}'
        "</script>"
    )
    products = extract_products_from_html(html, "https://shop.example/")
    assert len(products) == 1
    assert products[0].name == "Defy"


def test_extract_product_links_woocommerce_same_host_deduped():
    html = """
    <a href="https://shop.example/pr/a/" class="woocommerce-LoopProduct-link woocommerce-loop-product__link">A</a>
    <a class="woocommerce-LoopProduct-link" href="/pr/b/">B</a>
    <a href="https://shop.example/pr/a/" class="woocommerce-LoopProduct-link">dup</a>
    <a href="https://other.example/pr/c/" class="woocommerce-LoopProduct-link">offsite</a>
    """
    links = extract_product_links(html, "https://shop.example/kat/discs/")
    assert links == [
        "https://shop.example/pr/a/",
        "https://shop.example/pr/b/",
    ]


def test_extract_next_page_url():
    html = '<a class="next page-numbers" href="/kat/discs/page/2/">Next</a>'
    assert extract_next_page_url(html, "https://shop.example/kat/discs/") == (
        "https://shop.example/kat/discs/page/2/"
    )
    assert extract_next_page_url("<p>no pagination</p>", "https://shop.example/") is None


# --- Improved scanner: crawl orchestration ---------------------------------


def _product_page(name):
    return (
        '<script type="application/ld+json">'
        f'{{"@type":"Product","name":"{name}","brand":{{"@type":"Brand","name":"Axiom"}}}}'
        "</script>"
    )


def test_scan_crawls_listing_and_follows_pagination():
    pages = {
        "https://shop.example/kat/discs/": """
            <a class="woocommerce-LoopProduct-link" href="/pr/a/">A</a>
            <a class="woocommerce-LoopProduct-link" href="/pr/b/">B</a>
            <a class="next page-numbers" href="/kat/discs/page/2/">Next</a>
        """,
        "https://shop.example/kat/discs/page/2/": """
            <a class="woocommerce-LoopProduct-link" href="/pr/c/">C</a>
        """,
        "https://shop.example/pr/a/": _product_page("Axiom A | Midrange | shop"),
        "https://shop.example/pr/b/": _product_page("Axiom B | Putter | shop"),
        "https://shop.example/pr/c/": _product_page("Axiom C | Driver | shop"),
    }
    products = scan_products_from_url(
        "https://shop.example/kat/discs/",
        fetch=lambda url, timeout=10: pages[url],
        can_fetch=lambda url: True,
    )
    names = sorted(p.name for p in products)
    assert names == ["Axiom A", "Axiom B", "Axiom C"]


def test_scan_returns_direct_products_without_crawling():
    calls = []

    def fetch(url, timeout=10):
        calls.append(url)
        return _product_page("Solo Disc | Midrange | shop")

    products = scan_products_from_url(
        "https://shop.example/pr/solo/",
        fetch=fetch,
        can_fetch=lambda url: True,
    )
    assert [p.name for p in products] == ["Solo Disc"]
    # A product page yields products directly, so no extra crawling happens.
    assert calls == ["https://shop.example/pr/solo/"]


def test_scan_respects_max_products_cap():
    listing = "".join(
        f'<a class="woocommerce-LoopProduct-link" href="/pr/{i}/">P</a>'
        for i in range(10)
    )
    pages = {"https://shop.example/kat/discs/": listing}
    for i in range(10):
        pages[f"https://shop.example/pr/{i}/"] = _product_page(f"Disc {i}")

    products = scan_products_from_url(
        "https://shop.example/kat/discs/",
        fetch=lambda url, timeout=10: pages[url],
        can_fetch=lambda url: True,
        max_products=3,
    )
    assert len(products) == 3


# --- Disc data enrichment (flight numbers, type, image, description) --------

from app.scanner import extract_meta_description, parse_flight_numbers  # noqa: E402


def test_parse_flight_numbers_including_negative_turn():
    text = "Distance Driver Disc - Speed: 11 - Glide: 5 - Turn: -1 - Fade: 3."
    assert parse_flight_numbers(text) == {"speed": 11, "glide": 5, "turn": -1, "fade": 3}


def test_parse_flight_numbers_missing_returns_none():
    assert parse_flight_numbers("no numbers here") == {
        "speed": None,
        "glide": None,
        "turn": None,
        "fade": None,
    }


def test_extract_meta_description_prefers_name_description():
    html = (
        '<meta name="description" content="Die Axiom Defy - Speed: 11">'
        '<meta property="og:description" content="fallback">'
    )
    assert extract_meta_description(html) == "Die Axiom Defy - Speed: 11"


def test_extract_meta_description_falls_back_to_og():
    html = '<meta property="og:description" content="Only OG description">'
    assert extract_meta_description(html) == "Only OG description"


def test_extract_products_enriches_from_jsonld_and_meta():
    html = """
    <meta name="description" content="Die Axiom Defy ist eine &uuml;berstabile Distance Driver Disc - Speed: 11 - Glide: 5 - Turn: -1 - Fade: 3.">
    <script type="application/ld+json">
    {"@type":"Product","name":"Axiom Defy | Distance Driver | discgolf4you",
     "brand":{"@type":"Brand","name":"Axiom"},
     "category":"Discs &gt; Distance Driver",
     "image":[{"@type":"ImageObject","url":"https://shop.example/img/defy.jpg"}],
     "url":"/pr/axiom-defy/"}
    </script>
    """
    products = extract_products_from_html(html, "https://shop.example/pr/axiom-defy/")
    assert len(products) == 1
    p = products[0]
    assert p.name == "Axiom Defy"
    assert p.manufacturer == "Axiom"
    assert p.disc_type == "Distance Driver"
    assert p.image_url == "https://shop.example/img/defy.jpg"
    assert (p.speed, p.glide, p.turn, p.fade) == (11, 5, -1, 3)
    assert "berstabile" in p.description


def test_extract_products_handles_image_as_plain_string():
    html = (
        '<script type="application/ld+json">'
        '{"@type":"Product","name":"Disc","image":"https://shop.example/x.jpg"}'
        "</script>"
    )
    products = extract_products_from_html(html, "https://shop.example/pr/x/")
    assert products[0].image_url == "https://shop.example/x.jpg"
