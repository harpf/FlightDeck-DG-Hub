from __future__ import annotations

import json
import re
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


# --- robots.txt ------------------------------------------------------------

def build_robots_url(source_url: str) -> str:
    parsed = urlparse(source_url)
    return urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))


def is_scraping_allowed(source_url: str, user_agent: str = SCANNER_USER_AGENT) -> bool:
    parser = RobotFileParser()
    parser.set_url(build_robots_url(source_url))
    parser.read()
    return parser.can_fetch(user_agent, source_url)


def _make_robots_checker(base_url: str) -> Callable[[str], bool]:
    """A reusable robots.txt checker for one host (read once, queried per URL)."""
    parser = RobotFileParser()
    parser.set_url(build_robots_url(base_url))
    try:
        parser.read()
    except Exception:
        # If robots.txt can't be read, fall back to allowing (best effort).
        return lambda _url: True
    return lambda url: parser.can_fetch(SCANNER_USER_AGENT, url)


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


def _disc_type_from_category(value: Any) -> str | None:
    """Last segment of a JSON-LD category, e.g. 'Discs > Distance Driver' -> 'Distance Driver'."""
    if not isinstance(value, str):
        return None
    parts = [part.strip() for part in html_unescape(value).split(">") if part.strip()]
    return parts[-1] if parts else None


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


def extract_products_from_html(html: str, base_url: str) -> list[ScannedProduct]:
    """Extract schema.org Product entries from a page, enriched with page metadata.

    Flight numbers and a prose description come from the page-level meta
    description; disc type and image come from the Product JSON-LD.
    """
    meta_description = extract_meta_description(html)
    flight = parse_flight_numbers(meta_description)
    products: list[ScannedProduct] = []
    seen: set[tuple[str, str | None]] = set()
    for obj in _iter_jsonld_objects(html):
        for entry in _iter_products(obj):
            name = clean_name(str(entry.get("name")))
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
                    disc_type=_disc_type_from_category(entry.get("category")),
                    image_url=urljoin(base_url, image_url) if image_url else None,
                    speed=flight["speed"],
                    glide=flight["glide"],
                    turn=flight["turn"],
                    fade=flight["fade"],
                )
            )
    return products


def extract_product_links(html: str, base_url: str) -> list[str]:
    """Same-host product-page links from a WooCommerce listing page, deduped."""
    host = urlparse(base_url).netloc
    links: list[str] = []
    seen: set[str] = set()
    for attrs in _ANCHOR_RE.findall(html):
        class_match = _CLASS_RE.search(attrs)
        if not class_match or _PRODUCT_LINK_MARKER not in class_match.group(1).lower():
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


def scan_products_from_url(
    source_url: str,
    *,
    fetch: Callable[..., str] | None = None,
    can_fetch: Callable[[str], bool] | None = None,
    max_pages: int = MAX_PAGES,
    max_products: int = MAX_PRODUCTS,
) -> list[ScannedProduct]:
    """Extract products from a product page, or crawl a listing page's products.

    If ``source_url`` is a single product page, its Product JSON-LD is returned
    directly. If it is a category/listing page (no Product data of its own), the
    linked product pages are fetched and their products collected, following
    pagination up to ``max_pages`` / ``max_products``.

    ``fetch`` and ``can_fetch`` are injectable for testing without network I/O.
    """
    if fetch is None:
        fetch = fetch_html

    page_html = fetch(source_url)
    direct = extract_products_from_html(page_html, source_url)
    if direct:
        return direct

    if can_fetch is None:
        can_fetch = _make_robots_checker(source_url)

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
            try:
                product_html = fetch(link)
            except Exception:
                continue
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
        try:
            page_html = fetch(page_url)
        except Exception:
            break

    return results
