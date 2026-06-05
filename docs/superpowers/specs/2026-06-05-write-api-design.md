# Design: Authenticated write API (scans, sources, products, reviews)

**Date:** 2026-06-05
**Area:** `app/models.py`, `app/routes.py`, `app/services.py` (new), `app/forms.py`,
`app/openapi.py`, `app/templates/admin/dashboard.html`, tests.

## Problem

The REST API is read-only (`GET` products / full export / health). Every writing
action — scanning a source, managing sources, creating/editing products, posting
reviews — is only reachable through the browser UI (session login + CSRF). The goal
is to expose those actions over the token API so the app can be driven entirely via API.

## Authorization model

API tokens are currently unscoped and used only for reads. Add a **scope flag**:

- New column `ApiToken.is_admin` (boolean, default `False`).
- **Read** endpoints: any active token (unchanged behaviour).
- **Write/admin** endpoints: require `is_admin` token, else `403`.
- Token creation (admin dashboard) gets an "Admin (Schreibrechte)" checkbox.

Decorators (factor shared token resolution into one helper to avoid duplication):

- `api_token_required` — resolve + verify token (existing reads).
- `api_admin_token_required` — same, then require `g.api_token.is_admin` (`403` if not).

The acting user for writes is the token's creator (`token.created_by`), reused as the
requester/author where a `User` is needed (source requests, reviews).

## Endpoints (all JSON in/out, under `/api/v1`)

**Products**
- `POST /products` (admin) — create. `name` required; `category` defaults `"Disc"`;
  optional `manufacturer, description, product_url, image_url, disc_type, speed,
  glide, turn, fade, diameter_cm, weight_range_g, plastic_type, stability`. → `201` + product.
- `PATCH /products/{id}` (admin) — partial update of any of the above. → `200` + product; `404` if missing.
- `DELETE /products/{id}` (admin) — → `204`; `404` if missing.

**Sources**
- `POST /sources` (admin) — `source_url` required, optional `note`, optional
  `status` (default `"open"`). Requester = token creator. → `201` + source.
- `PATCH /sources/{id}` (admin) — update `status` (`open|approved|rejected`). → `200` + source.
- `POST /sources/{id}/scan` (admin) — run the import on an **approved** source.
  → `200` `{ "found": n, "created": n, "duplicates": n }`; `409` if not approved;
  `403`-style JSON if robots.txt forbids.

**Reviews**
- `POST /products/{id}/reviews` (admin) — `rating` (1–5) required, optional `comment`.
  Author = token creator; upserts that user's review (matches web behaviour). → `201`/`200` + review.

**Errors:** `400` invalid/missing body fields, `401` bad/missing token, `403`
insufficient scope, `404` missing resource, `409` precondition (e.g. scan on
non-approved source). All as `{"error": "..."}`.

## Shared logic (DRY)

Extract the scan-and-store core currently inline in the web `admin.scan_source`
route into `app/services.py`:

- `import_products_from_source(source_request) -> dict` — robots check (raises a
  typed error if forbidden), `scan_products_from_url`, dedup-insert by
  `(name, manufacturer)`, commit, return `{found, created, duplicates}`.
- `upsert_review(user, product, rating, comment) -> (review, created: bool)`.

Both the web routes and the new API endpoints call these, so behaviour can't drift.
The web `scan_source` route is refactored to use the service (its flash messages and
redirects stay identical — covered by the existing `test_admin_scan.py`).

## OpenAPI / Swagger (`app/openapi.py`)

The spec is a hand-maintained dict. Add: request-body schemas (`ProductInput`,
`SourceInput`, `ReviewInput`), the new paths above (each tagged and marked
`security: [{ApiTokenAuth: []}]` with a note that writes need an admin token), and
new tags (`Admin`). The embedded Swagger UI then documents the full surface.

## Model migration

`init-db` uses `create_all` (won't alter an existing table). Deployment runs an
idempotent `ALTER TABLE api_token ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0`,
then the admin re-creates (or marks) a token as admin to use the write API.

## Testing (TDD)

- Scope: a read token gets `403` on a write endpoint; an admin token succeeds.
- Product create / patch / delete round-trips (and `404`s).
- Source create + `PATCH` status; `POST /scan` returns counts (scanner monkeypatched),
  and `409` when the source isn't approved.
- Review create via API upserts for the token's user.
- `import_products_from_source` unit test (dedup + counts) with a fake scanner.
- OpenAPI spec contains the new paths and input schemas.
- Existing read-API, scan, and web tests stay green (web `scan_source` behaviour
  unchanged after the service refactor).

## Non-goals

- Issuing/rotating tokens via API (still admin-UI only) — avoids a privilege-escalation
  surface where an admin token mints more tokens.
- User registration/login or user management via API.
- Pagination/rate-limiting on writes (out of scope for this exam project).

## Risks / trade-offs

- An admin-scoped token is powerful (full write). It's created deliberately in the
  admin UI and can be deactivated there; documented as such.
- Hand-maintained OpenAPI can drift; mitigated by a test asserting the new paths exist.
