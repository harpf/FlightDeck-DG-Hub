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


# --- Crawler improvements: extra fields, generic links, politeness ---------

from app.scanner import (  # noqa: E402
    parse_price,
    parse_stability,
    parse_weight_grams,
)


def test_parse_price_from_aggregate_offer():
    entry = {"offers": {"@type": "AggregateOffer", "lowPrice": "22.90", "priceCurrency": "EUR"}}
    assert parse_price(entry) == "22.90 EUR"


def test_parse_price_from_offer_list():
    entry = {"offers": [{"@type": "Offer", "price": "19.90", "priceCurrency": "CHF"}]}
    assert parse_price(entry) == "19.90 CHF"


def test_parse_weight_kgm_to_grams():
    entry = {"weight": {"@type": "QuantitativeValue", "unitCode": "KGM", "value": "0.200"}}
    assert parse_weight_grams(entry) == "200 g"


def test_parse_stability_keywords():
    assert parse_stability("eine überstabile Distance Driver Disc") == "überstabil"
    assert parse_stability("understable Putter") == "understabil"
    assert parse_stability("stabiler Midrange") == "stabil"
    assert parse_stability("keine Angabe") is None


def test_extract_products_populates_price_weight_stability():
    html = """
    <meta name="description" content="Die Axiom Defy ist eine überstabile Distance Driver Disc - Speed: 11 - Glide: 5 - Turn: -1 - Fade: 3.">
    <script type="application/ld+json">
    {"@type":"Product","name":"Axiom Defy | Distance Driver | shop",
     "brand":{"@type":"Brand","name":"Axiom"},
     "weight":{"@type":"QuantitativeValue","unitCode":"KGM","value":"0.175"},
     "offers":{"@type":"AggregateOffer","lowPrice":"22.90","priceCurrency":"EUR"},
     "url":"/pr/axiom-defy/"}
    </script>
    """
    p = extract_products_from_html(html, "https://shop.example/pr/axiom-defy/")[0]
    assert p.price == "22.90 EUR"
    assert p.weight_range_g == "175 g"
    assert p.stability == "überstabil"


def test_extract_product_links_generic_fallback_non_woocommerce():
    html = """
    <a href="/shop/disc-a/" class="product-tile__link">A</a>
    <a href="/shop/disc-b/" class="card product link-primary">B</a>
    <a href="/kategorie/discs/" class="product-category-link">Kategorie</a>
    """
    links = extract_product_links(html, "https://shop.example/discs/")
    assert links == [
        "https://shop.example/shop/disc-a/",
        "https://shop.example/shop/disc-b/",
    ]


def test_woocommerce_links_take_precedence_over_generic():
    # A page with WooCommerce tiles must NOT also pull in unrelated product-ish links.
    html = """
    <a href="/pr/real/" class="woocommerce-LoopProduct-link">real</a>
    <a href="/misc/" class="some-product-link">noise</a>
    """
    links = extract_product_links(html, "https://shop.example/kat/")
    assert links == ["https://shop.example/pr/real/"]


def test_scan_sleeps_between_product_fetches():
    pages = {
        "https://shop.example/kat/": '<a class="woocommerce-LoopProduct-link" href="/pr/a/">A</a>',
        "https://shop.example/pr/a/": _product_page("Axiom A | Midrange | shop"),
    }
    calls = []
    scan_products_from_url(
        "https://shop.example/kat/",
        fetch=lambda url, timeout=10: pages[url],
        can_fetch=lambda url: True,
        sleep=lambda seconds: calls.append(seconds),
        delay=0.2,
    )
    assert calls, "expected the crawler to pause between requests"


def test_disc_type_falls_back_to_title_when_category_is_generic():
    # JSON-LD category is only "Discs" -> use the middle title segment "Putter".
    html = (
        '<script type="application/ld+json">'
        '{"@type":"Product","name":"Axiom Bokeh | Putter | discgolf4you","category":"Discs"}'
        "</script>"
    )
    p = extract_products_from_html(html, "https://shop.example/pr/bokeh/")[0]
    assert p.name == "Axiom Bokeh"
    assert p.disc_type == "Putter"


def test_disc_type_prefers_specific_category():
    html = (
        '<script type="application/ld+json">'
        '{"@type":"Product","name":"Axiom Defy | Distance Driver | shop","category":"Discs &gt; Distance Driver"}'
        "</script>"
    )
    p = extract_products_from_html(html, "https://shop.example/pr/defy/")[0]
    assert p.disc_type == "Distance Driver"


def test_scan_retries_a_failing_product_fetch_once():
    attempts = {"count": 0}

    def fetch(url, timeout=10):
        if url == "https://shop.example/kat/":
            return '<a class="woocommerce-LoopProduct-link" href="/pr/a/">A</a>'
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise OSError("temporary")
        return _product_page("Axiom A | Midrange | shop")

    products = scan_products_from_url(
        "https://shop.example/kat/",
        fetch=fetch,
        can_fetch=lambda url: True,
        sleep=lambda seconds: None,
    )
    assert [p.name for p in products] == ["Axiom A"]
    assert attempts["count"] == 2  # failed once, retried, succeeded
