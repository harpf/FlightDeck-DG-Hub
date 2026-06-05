from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
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


@dataclass
class ScannedProduct:
    name: str
    description: str | None
    manufacturer: str | None
    product_url: str


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


def extract_products_from_html(html: str, base_url: str) -> list[ScannedProduct]:
    """Extract all schema.org Product entries from a page's JSON-LD."""
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
            products.append(
                ScannedProduct(
                    name=name,
                    description=entry.get("description"),
                    manufacturer=manufacturer,
                    product_url=urljoin(base_url, raw_url),
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
