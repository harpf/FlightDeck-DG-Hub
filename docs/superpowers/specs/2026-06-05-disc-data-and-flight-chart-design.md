# Design: Full disc data + image + flight-path chart

**Date:** 2026-06-05
**Area:** `app/scanner.py`, `app/models.py`, `app/routes.py`, `app/flightchart.py` (new),
`app/templates/products/detail.html`, tests.

## Problem

Scanned discs import with empty fields: no flight numbers, no real description,
generic `category='Disc'`, no `disc_type`, and no image. The detail page already
renders a "Flugwerte" section and a tech-data card, but they are blank, and there
is no product image and no flight visualization.

The data is available on each WooCommerce product page:

- **Speed/Glide/Turn/Fade** and a prose **description** are in the page's
  `<meta name="description">` (e.g. `… Distance Driver Disc - Speed: 11 - Glide: 5
  - Turn: -1 - Fade: 3.`).
- **disc_type** is in JSON-LD `category` (`"Discs > Distance Driver"` -> `"Distance Driver"`).
- **image** is in JSON-LD `image[].url`.

## Goals

1. Scanner fills `description`, `disc_type`, `speed`, `glide`, `turn`, `fade`, and a
   new `image_url` for each scanned disc.
2. The detail page shows the disc image.
3. The detail page shows a **top-down flight-path chart** generated server-side as
   inline SVG from the four flight numbers (no JS, no external library).

## Non-goals

- Per-weight/colour variants, price, stock. Only the catalogue disc record.
- A physically accurate flight simulation. The chart is the conventional
  flight-rating trajectory used across disc-golf sites, not aerodynamics.

## Design

### Scanner (`app/scanner.py`)

Extend `ScannedProduct` with `disc_type`, `image_url`, `speed`, `glide`, `turn`,
`fade` (the four numbers are `int | None`).

New pure helpers (unit-tested, no network):

- `parse_flight_numbers(text) -> dict` — regex `Speed/Glide/Turn/Fade:\s*(-?\d+)`
  (case-insensitive) out of any text; missing keys -> `None`.
- `extract_meta_description(html) -> str | None` — `<meta name="description"
  content="...">`, falling back to `og:description`; HTML-unescaped.
- `_disc_type_from_category(value) -> str | None` — last `>`-separated segment of
  a JSON-LD `category` string, HTML-unescaped (`"Discs > Distance Driver"` ->
  `"Distance Driver"`).
- `_image_url(entry) -> str | None` — first URL from JSON-LD `image`, which may be a
  string, an `ImageObject` dict (`.url`), or a list of either.

`extract_products_from_html` now also reads the page-level meta description once and
merges its description + flight numbers into the product(s) found on that page
(product pages carry exactly one Product). `clean_name` and crawl logic unchanged.

### Model (`app/models.py`)

Add `image_url = db.Column(db.String(500))` to `Product`. Flight/type columns already
exist. Live DB: `init-db` uses `create_all` (won't alter an existing table), so the
deployment step runs an idempotent `ALTER TABLE product ADD COLUMN image_url
VARCHAR(500)` before re-scanning.

### Flight chart (`app/flightchart.py`, new)

Pure geometry, fully unit-testable, returns plain data + an SVG string:

- `flight_path_points(turn, fade, *, width, height, n) -> list[(x, y)]`
  Top-down trajectory, release at bottom-centre, distance upward. For a RHBH throw:
  - `turn` (negative = high-speed turn right): a transient rightward bulge,
    `amp_turn * (-turn) * sin(pi*t)` (zero at release and landing).
  - `fade` (positive = low-speed finish left): a late leftward pull ramping in after
    mid-flight, so the disc **lands left of centre** for overstable discs.
  - Straight disc (`turn=0, fade=0`) -> path stays on the centre line.
- `render_flight_svg(speed, glide, turn, fade, ...) -> Markup` — builds an SVG
  (centre guide line, release dot, the polyline path, small S/G/T/F caption). Returns
  `markupsafe.Markup` so Jinja renders it inline. Returns `None` when no flight
  numbers exist (template then omits the chart).

Amplitudes are chosen so the widest realistic values (turn -5, fade 5) stay within
the SVG box.

### Route + template

- `admin.scan_source`: persist the new fields when creating `Product`
  (`disc_type`, `image_url`, `speed`, `glide`, `turn`, `fade`); keep `category='Disc'`.
- `products.product_detail`: pass `flight_svg = render_flight_svg(...)` to the template.
- `detail.html`: show `<img>` when `product.image_url`; render `flight_svg` (inside the
  existing Flugwerte block) when present.

## Testing

- `parse_flight_numbers` extracts all four (incl. negative turn) and tolerates missing.
- `extract_meta_description` reads name=description and falls back to og:description.
- `extract_products_from_html` on a real-shaped product page yields a product with
  flight numbers, disc_type, image_url, and description populated.
- `_image_url` handles string / ImageObject / list forms.
- `flight_path_points`: overstable lands left of centre; understable bulges right and
  lands near centre; straight stays centred; all points within the box.
- `render_flight_svg` returns `None` without numbers and SVG markup with them.
- Route test: scanning persists the new fields onto the `Product` row.
- Existing scanner/route/web tests stay green.

## Risks / trade-offs

- Flight numbers are parsed from the meta description; a shop that omits them yields
  `None` (chart hidden) — acceptable and reported by the existing "found/new" counts.
- The chart is illustrative (flight-rating convention), not a physics model — stated
  in a caption/tooltip.
- `image_url` shows a hotlinked shop image; acceptable for this catalogue use.
