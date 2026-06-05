# Design: Robust product scanner (JSON-LD + listing crawl)

**Date:** 2026-06-05
**Area:** `app/scanner.py`, `app/routes.py` (`admin.scan_source`), `tests/test_scanner.py`

## Problem

Scanning a source URL reports "Scan abgeschlossen. Neue Einträge: 0" with no error.

Root cause: the target sites are WooCommerce shops (e.g.
`https://discgolf4you.com/kat/discs/`). A **category/listing** page exposes only
`Organization` / `WebSite` / `CollectionPage` / `BreadcrumbList` JSON-LD — **no
`Product`**. The products are links (`woocommerce-LoopProduct-link`) to individual
pages such as `/pr/axiom-balance/`, and only *those* pages carry `Product` JSON-LD.

The current scanner (`scan_products_from_url`) only matches **top-level**
`@type == "Product"` on the single page it is given, so on a listing page it
correctly finds nothing. Two gaps:

1. **Extraction too strict** — misses `Product` nested under `@graph`, inside
   arrays, or when `@type` is a list (`["Product", ...]`). Even a single product
   page can be missed.
2. **No crawl** — a listing page is never followed to its product pages.

A secondary issue: the "0" message is ambiguous (nothing found vs. all duplicates),
and a network failure raises → 500 page instead of a clean message.

## Goals

- Scanning a WooCommerce **category URL** discovers and imports its products.
- Scanning a single **product URL** still works (and now also when nested in `@graph`).
- Clear admin feedback: found / new / duplicate counts, and graceful error messages.
- **No new dependencies** — standard library only (`urllib`, `re`, `json`).
- Polite + bounded crawling (caps, timeouts, robots.txt respected per page).

## Non-goals

- A general-purpose scraper for arbitrary (non-JSON-LD) shops. JSON-LD `Product`
  remains the data contract; listing crawl only *finds* the product pages to read.
- Rendering JavaScript / headless browser. WooCommerce emits JSON-LD server-side.
- Parsing flight numbers / price / images. Only name, description, manufacturer,
  product_url (today's `ScannedProduct` shape) are imported.

## Design

### `app/scanner.py` — split pure parsing from network I/O

Pure functions (no network → directly unit-testable):

- `clean_name(raw: str) -> str` — return the first `|`-separated segment, stripped.
  `"Axiom Balance | Midrange | discgolf4you"` → `"Axiom Balance"`.
- `iter_jsonld_objects(html) -> Iterator[Any]` — find every
  `<script type="application/ld+json">` block and `json.loads` it (skip invalid).
- `iter_products(node) -> Iterator[dict]` — **recursively** walk dicts (including
  `@graph`) and lists, yielding any dict whose `@type` is `"Product"` or whose
  `@type` list contains `"Product"`.
- `extract_products_from_html(html, base_url) -> list[ScannedProduct]` — combine the
  two above; build `ScannedProduct(name=clean_name(...), description, manufacturer
  from brand.name, product_url=absolute(url or base_url))`. Dedup within a page by
  (name, manufacturer).
- `extract_product_links(html, base_url) -> list[str]` — anchors whose class
  contains `woocommerce-LoopProduct-link` (both attribute orders), with a generic
  fallback (`<a class="...product...link...">`). Resolve to absolute, keep
  **same-host** only, dedup preserving order.
- `extract_next_page_url(html, base_url) -> str | None` — WooCommerce
  `<a class="next page-numbers" href="...">`, resolved absolute (else `None`).

Network functions:

- `fetch_html(url, timeout=DEFAULT_TIMEOUT) -> str` — `Request` with
  `SCANNER_USER_AGENT`, `urlopen`, decode utf-8 (errors ignored). Wraps existing
  logic so the existing `urlopen` monkeypatch in tests keeps working.
- `scan_products_from_url(source_url, *, fetch=fetch_html, can_fetch=None,
  max_pages=MAX_PAGES, max_products=MAX_PRODUCTS) -> list[ScannedProduct]`
  — orchestration:
  1. Fetch `source_url`; `direct = extract_products_from_html(...)`.
  2. If `direct` non-empty → it's a product page → return `direct`.
  3. Else treat as a listing. Build a single robots checker for the host (unless
     `can_fetch` injected). Loop up to `max_pages`:
     - `extract_product_links(page_html, page_url)`.
     - For each link: skip if robots disallows; `fetch` it; extend results with its
       products; stop once `len(results) >= max_products`.
     - `next = extract_next_page_url(page_html, page_url)`; stop if `None` or cap hit.
  4. Dedup results by `product_url` (fallback name); return.
  - Per-link `fetch` failures are caught and skipped (one bad page ≠ whole scan fails).
  - `fetch` and `can_fetch` are injectable so tests run without network.

Constants: `DEFAULT_TIMEOUT = 10`, `MAX_PAGES = 25`, `MAX_PRODUCTS = 500`.

### `app/routes.py` — `admin.scan_source` feedback

- Wrap the `scan_products_from_url` call in `try/except Exception` → on failure,
  `flash("Scan fehlgeschlagen: <message>", "danger")` and redirect (no 500).
- Track `found = len(scanned)`, `created`, and `duplicates` (existing-name skips).
- Flash messages:
  - `found == 0`: `"Keine strukturierten Produktdaten gefunden (JSON-LD)."` — `warning`.
  - otherwise: `"Scan abgeschlossen: {found} gefunden, {created} neu, {duplicates}
    bereits vorhanden."` — `success`.
- `robots.txt` disallow path unchanged (already flashes `danger`).

### Crawl scope & politeness

- Follows pagination (user choice) but bounded by `MAX_PAGES` and `MAX_PRODUCTS`.
- Each request uses `DEFAULT_TIMEOUT`; robots.txt checked once per host and reused.
- Same-host restriction prevents wandering off-site via stray links.

## Testing (`tests/test_scanner.py`, extends existing monkeypatch style)

- `clean_name` trims multi-segment titles.
- `extract_products_from_html` finds a `Product` nested in `@graph`.
- `iter_products` matches `@type` given as a list.
- `extract_product_links` pulls WooCommerce loop links, same-host, deduped.
- `extract_next_page_url` returns the `next page-numbers` href (and `None` when absent).
- `scan_products_from_url` with an injected `fetch` (dict `url -> html`: listing
  page 1 with links + next → page 2 with links; product pages → Product JSON-LD)
  and `can_fetch=lambda u: True` returns the expected products and honours the caps.
- Existing `test_scan_products_from_url` (single product page via `urlopen`
  monkeypatch) continues to pass unchanged.

## Risks / trade-offs

- Following pagination means a large category = many requests / slower scan; the
  `MAX_PAGES`/`MAX_PRODUCTS` caps bound it (and are logged in the flash count so a
  truncated scan is visible).
- Sites without server-side JSON-LD `Product` data still yield 0 — now reported
  explicitly rather than silently.
