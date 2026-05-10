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
