from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from html import unescape as html_unescape
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser


SCANNER_USER_AGENT = "FlightDeckScanner/1.0"

# Safety limits so a listing crawl stays bounded and polite to the target host.
DEFAULT_TIMEOUT = 10
MAX_PAGES = 25
MAX_PRODUCTS = 500
# Politeness: pause between requests. Honour robots.txt Crawl-delay up to a cap;
# otherwise use a small default so we never hammer a shop.
DEFAULT_DELAY = 0.5
MAX_DELAY = 5.0
DEFAULT_RETRIES = 1

_JSONLD_RE = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
    flags=re.DOTALL | re.IGNORECASE,
)
_ANCHOR_RE = re.compile(r"<a\b([^>]*)>", flags=re.IGNORECASE)
_HREF_RE = re.compile(r'href="([^"]+)"', flags=re.IGNORECASE)
_CLASS_RE = re.compile(r'class="([^"]*)"', flags=re.IGNORECASE)
# WooCommerce renders each catalogue tile as <a class="woocommerce-LoopProduct-link ...">
_PRODUCT_LINK_MARKER = "woocommerce-loopproduct-link"

_META_RE = re.compile(r"<meta\b([^>]*)>", flags=re.IGNORECASE)
_NAME_ATTR_RE = re.compile(r'name="([^"]*)"', flags=re.IGNORECASE)
_PROP_ATTR_RE = re.compile(r'property="([^"]*)"', flags=re.IGNORECASE)
_CONTENT_ATTR_RE = re.compile(r'content="([^"]*)"', flags=re.IGNORECASE)
# Flight numbers live in prose like "... - Speed: 11 - Glide: 5 - Turn: -1 - Fade: 3."
_FLIGHT_RES = {
    key: re.compile(rf"{key}\s*:\s*(-?\d+)", flags=re.IGNORECASE)
    for key in ("Speed", "Glide", "Turn", "Fade")
}


@dataclass
class ScannedProduct:
    name: str
    description: str | None
    manufacturer: str | None
    product_url: str
    disc_type: str | None = None
    image_url: str | None = None
    speed: int | None = None
    glide: int | None = None
    turn: int | None = None
    fade: int | None = None
    price: str | None = None
    weight_range_g: str | None = None
    stability: str | None = None


# --- robots.txt ------------------------------------------------------------

def build_robots_url(source_url: str) -> str:
    parsed = urlparse(source_url)
    return urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))


def is_scraping_allowed(source_url: str, user_agent: str = SCANNER_USER_AGENT) -> bool:
    parser = RobotFileParser()
    parser.set_url(build_robots_url(source_url))
    parser.read()
    return parser.can_fetch(user_agent, source_url)


def _robots_for(base_url: str) -> tuple[Callable[[str], bool], float | None]:
    """Read robots.txt once and return (can_fetch checker, crawl-delay seconds)."""
    parser = RobotFileParser()
    parser.set_url(build_robots_url(base_url))
    try:
        parser.read()
    except Exception:
        # If robots.txt can't be read, fall back to allowing (best effort).
        return (lambda _url: True), None
    try:
        crawl_delay = parser.crawl_delay(SCANNER_USER_AGENT)
        delay = float(crawl_delay) if crawl_delay is not None else None
    except Exception:
        delay = None
    return (lambda url: parser.can_fetch(SCANNER_USER_AGENT, url)), delay


def _make_robots_checker(base_url: str) -> Callable[[str], bool]:
    """Backward-compatible robots checker (delegates to :func:`_robots_for`)."""
    checker, _delay = _robots_for(base_url)
    return checker


# --- pure parsing helpers (no network) -------------------------------------

def clean_name(raw: str) -> str:
    """Trim a shop title to its first ``|``-separated segment.

    ``"Axiom Balance | Midrange | discgolf4you"`` -> ``"Axiom Balance"``.
    """
    return raw.split("|")[0].strip()


def _iter_jsonld_objects(html: str) -> Iterator[Any]:
    for raw in _JSONLD_RE.findall(html):
        try:
            yield json.loads(raw.strip())
        except json.JSONDecodeError:
            continue


def _is_product(node: dict) -> bool:
    node_type = node.get("@type")
    if isinstance(node_type, list):
        return "Product" in node_type
    return node_type == "Product"


def _iter_products(node: Any) -> Iterator[dict]:
    """Recursively yield Product dicts, descending into ``@graph`` and arrays."""
    if isinstance(node, dict):
        if _is_product(node) and node.get("name"):
            yield node
        for value in node.values():
            yield from _iter_products(value)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_products(value)


def _brand_name(entry: dict) -> str | None:
    brand = entry.get("brand")
    if isinstance(brand, dict):
        return brand.get("name")
    if isinstance(brand, str):
        return brand
    return None


def parse_flight_numbers(text: str | None) -> dict[str, int | None]:
    """Pull Speed/Glide/Turn/Fade integers out of prose; missing -> None."""
    result: dict[str, int | None] = {}
    for label, regex in _FLIGHT_RES.items():
        match = regex.search(text or "")
        result[label.lower()] = int(match.group(1)) if match else None
    return result


def extract_meta_description(html: str) -> str | None:
    """Page description from <meta name="description">, falling back to og:description."""
    description: str | None = None
    og_description: str | None = None
    for attrs in _META_RE.findall(html):
        content = _CONTENT_ATTR_RE.search(attrs)
        if not content:
            continue
        name = _NAME_ATTR_RE.search(attrs)
        prop = _PROP_ATTR_RE.search(attrs)
        if name and name.group(1).lower() == "description" and description is None:
            description = content.group(1)
        elif prop and prop.group(1).lower() == "og:description" and og_description is None:
            og_description = content.group(1)
    chosen = description or og_description
    return html_unescape(chosen) if chosen else None


# Category values too generic to be a useful disc type on their own.
_GENERIC_DISC_TYPES = {"disc", "discs"}


def _disc_type_from_category(value: Any) -> str | None:
    """Last segment of a JSON-LD category, e.g. 'Discs > Distance Driver' -> 'Distance Driver'."""
    if not isinstance(value, str):
        return None
    parts = [part.strip() for part in html_unescape(value).split(">") if part.strip()]
    if not parts:
        return None
    candidate = parts[-1]
    return None if candidate.lower() in _GENERIC_DISC_TYPES else candidate


def _disc_type_from_title(raw_title: str) -> str | None:
    """Middle segment of a shop title, e.g. 'Axiom Bokeh | Putter | shop' -> 'Putter'."""
    parts = [part.strip() for part in raw_title.split("|")]
    return parts[1] if len(parts) >= 3 and parts[1] else None


def _disc_type(entry: dict, raw_title: str) -> str | None:
    """Disc type from JSON-LD category, falling back to the title's middle segment."""
    return _disc_type_from_category(entry.get("category")) or _disc_type_from_title(raw_title)


def _first_image_url(image: Any) -> str | None:
    """First URL from a JSON-LD image (string, ImageObject dict, or list of either)."""
    if isinstance(image, str):
        return image
    if isinstance(image, dict):
        return image.get("url")
    if isinstance(image, list):
        for item in image:
            url = _first_image_url(item)
            if url:
                return url
    return None


def _first_offer(entry: dict) -> dict | None:
    offers = entry.get("offers")
    if isinstance(offers, dict):
        return offers
    if isinstance(offers, list):
        for offer in offers:
            if isinstance(offer, dict):
                return offer
    return None


def parse_price(entry: dict) -> str | None:
    """Price + currency from JSON-LD offers, e.g. 'lowPrice 22.90 EUR' -> '22.90 EUR'."""
    offer = _first_offer(entry)
    if not offer:
        return None
    price = offer.get("lowPrice") or offer.get("price")
    if price is None:
        return None
    currency = offer.get("priceCurrency")
    return f"{price} {currency}".strip() if currency else str(price)


def parse_weight_grams(entry: dict) -> str | None:
    """Weight in grams from a JSON-LD QuantitativeValue (KGM or GRM), e.g. '175 g'."""
    weight = entry.get("weight")
    if not isinstance(weight, dict):
        return None
    try:
        value = float(weight.get("value"))
    except (TypeError, ValueError):
        return None
    unit = (weight.get("unitCode") or "").upper()
    grams = value * 1000 if unit == "KGM" else value  # GRM or unspecified -> grams
    return f"{round(grams)} g"


# Stability keywords (German shop prose); order matters (check "überstabil" first).
_STABILITY_KEYWORDS = (
    ("überstabil", "überstabil"),
    ("overstable", "überstabil"),
    ("understabil", "understabil"),
    ("understable", "understabil"),
    ("understabel", "understabil"),
    ("stabil", "stabil"),
    ("neutral", "stabil"),
)


def parse_stability(text: str | None) -> str | None:
    """Classify stability from prose keywords, or ``None`` if unknown."""
    if not text:
        return None
    lowered = text.lower()
    for keyword, label in _STABILITY_KEYWORDS:
        if keyword in lowered:
            return label
    return None


def extract_products_from_html(html: str, base_url: str) -> list[ScannedProduct]:
    """Extract schema.org Product entries from a page, enriched with page metadata.

    Flight numbers, a prose description and stability come from the page-level
    meta description; disc type, image, price and weight come from the Product
    JSON-LD.
    """
    meta_description = extract_meta_description(html)
    flight = parse_flight_numbers(meta_description)
    stability = parse_stability(meta_description)
    products: list[ScannedProduct] = []
    seen: set[tuple[str, str | None]] = set()
    for obj in _iter_jsonld_objects(html):
        for entry in _iter_products(obj):
            raw_title = str(entry.get("name"))
            name = clean_name(raw_title)
            if not name:
                continue
            manufacturer = _brand_name(entry)
            key = (name, manufacturer)
            if key in seen:
                continue
            seen.add(key)
            raw_url = entry.get("url") or base_url
            image_url = _first_image_url(entry.get("image"))
            products.append(
                ScannedProduct(
                    name=name,
                    description=entry.get("description") or meta_description,
                    manufacturer=manufacturer,
                    product_url=urljoin(base_url, raw_url),
                    disc_type=_disc_type(entry, raw_title),
                    image_url=urljoin(base_url, image_url) if image_url else None,
                    speed=flight["speed"],
                    glide=flight["glide"],
                    turn=flight["turn"],
                    fade=flight["fade"],
                    price=parse_price(entry),
                    weight_range_g=parse_weight_grams(entry),
                    stability=stability,
                )
            )
    return products


def _woocommerce_link_class(cls: str) -> bool:
    return _PRODUCT_LINK_MARKER in cls


def _generic_product_link_class(cls: str) -> bool:
    # Fallback for non-WooCommerce shops: an anchor that looks like a product link
    # (class mentions "product" and "link") but is not a category/navigation link.
    return "product" in cls and "link" in cls and "categor" not in cls


def _collect_links(html: str, base_url: str, matches: Callable[[str], bool]) -> list[str]:
    host = urlparse(base_url).netloc
    links: list[str] = []
    seen: set[str] = set()
    for attrs in _ANCHOR_RE.findall(html):
        class_match = _CLASS_RE.search(attrs)
        if not class_match or not matches(class_match.group(1).lower()):
            continue
        href_match = _HREF_RE.search(attrs)
        if not href_match:
            continue
        absolute = urljoin(base_url, href_match.group(1))
        if urlparse(absolute).netloc != host or absolute in seen:
            continue
        seen.add(absolute)
        links.append(absolute)
    return links


def extract_product_links(html: str, base_url: str) -> list[str]:
    """Same-host product-page links from a listing page, deduped.

    Prefers WooCommerce's ``woocommerce-LoopProduct-link`` tiles; if a page has
    none, falls back to a generic "looks like a product link" heuristic so other
    shops can be crawled too.
    """
    woo = _collect_links(html, base_url, _woocommerce_link_class)
    if woo:
        return woo
    return _collect_links(html, base_url, _generic_product_link_class)


def extract_next_page_url(html: str, base_url: str) -> str | None:
    """The WooCommerce ``next page-numbers`` link, absolute, or ``None``."""
    for attrs in _ANCHOR_RE.findall(html):
        class_match = _CLASS_RE.search(attrs)
        if not class_match:
            continue
        classes = class_match.group(1).lower().split()
        if "next" in classes and "page-numbers" in classes:
            href_match = _HREF_RE.search(attrs)
            if href_match:
                return urljoin(base_url, href_match.group(1))
    return None


# --- network + orchestration ----------------------------------------------

def fetch_html(url: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    req = Request(url, headers={"User-Agent": SCANNER_USER_AGENT})
    with urlopen(req, timeout=timeout) as response:  # noqa: S310
        return response.read().decode("utf-8", errors="ignore")


def _fetch_with_retry(fetch: Callable[..., str], url: str, retries: int, sleep: Callable[[float], None]) -> str:
    """Fetch a URL, retrying transient failures ``retries`` times with a short pause."""
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return fetch(url)
        except Exception as exc:  # network hiccup — brief pause, then retry
            last_error = exc
            if attempt < retries:
                sleep(0.5)
    raise last_error  # type: ignore[misc]


def scan_products_from_url(
    source_url: str,
    *,
    fetch: Callable[..., str] | None = None,
    can_fetch: Callable[[str], bool] | None = None,
    max_pages: int = MAX_PAGES,
    max_products: int = MAX_PRODUCTS,
    sleep: Callable[[float], None] | None = None,
    delay: float | None = None,
    retries: int = DEFAULT_RETRIES,
) -> list[ScannedProduct]:
    """Extract products from a product page, or crawl a listing page's products.

    If ``source_url`` is a single product page, its Product JSON-LD is returned
    directly. If it is a category/listing page (no Product data of its own), the
    linked product pages are fetched and their products collected, following
    pagination up to ``max_pages`` / ``max_products``.

    Politeness: pauses ``delay`` seconds between requests (from robots.txt
    Crawl-delay when available, else :data:`DEFAULT_DELAY`, capped at
    :data:`MAX_DELAY`) and retries a failed fetch ``retries`` times.

    ``fetch``, ``can_fetch`` and ``sleep`` are injectable for testing without I/O.
    """
    if fetch is None:
        fetch = fetch_html
    if sleep is None:
        sleep = time.sleep

    page_html = _fetch_with_retry(fetch, source_url, retries, sleep)
    direct = extract_products_from_html(page_html, source_url)
    if direct:
        return direct

    # Resolve robots checker + crawl-delay once for the host.
    robots_delay: float | None = None
    if can_fetch is None:
        can_fetch, robots_delay = _robots_for(source_url)
    if delay is None:
        delay = min(robots_delay if robots_delay is not None else DEFAULT_DELAY, MAX_DELAY)

    results: list[ScannedProduct] = []
    seen_products: set[str] = set()
    seen_pages: set[str] = set()
    page_url: str | None = source_url
    pages_done = 0

    while page_url and pages_done < max_pages and len(results) < max_products:
        seen_pages.add(page_url)
        for link in extract_product_links(page_html, page_url):
            if len(results) >= max_products:
                break
            if not can_fetch(link):
                continue
            sleep(delay)  # politeness pause before each product-page request
            try:
                product_html = _fetch_with_retry(fetch, link, retries, sleep)
            except Exception:
                continue  # one bad page must not abort the whole crawl
            for product in extract_products_from_html(product_html, link):
                key = product.product_url or product.name
                if key in seen_products:
                    continue
                seen_products.add(key)
                results.append(product)
                if len(results) >= max_products:
                    break
        pages_done += 1

        next_url = extract_next_page_url(page_html, page_url)
        if not next_url or next_url in seen_pages or len(results) >= max_products:
            break
        page_url = next_url
        sleep(delay)
        try:
            page_html = _fetch_with_retry(fetch, page_url, retries, sleep)
        except Exception:
            break

    return results
