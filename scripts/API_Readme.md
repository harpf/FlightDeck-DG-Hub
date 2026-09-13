# FlightDeck DG Hub — Web-API

A RESTful Web-API for selected application data (discs/products, reviews, source
requests). Read endpoints work with any active token; **write endpoints require
an admin-scoped token**. It is consumable with any HTTP client (curl, HTTPie,
Postman) **without a browser**.

## Interactive documentation (Swagger UI)

- **Swagger UI:** `GET /api/docs` — browse and "Try it out" against the live API
  (click *Authorize* and paste an `<id>.<secret>` token).
- **OpenAPI spec:** `GET /api/openapi.json` — the machine-readable OpenAPI 3.0
  document (also importable into Postman/Insomnia).

## Authentication

The API uses a **static API token**. An admin creates a token in the web UI
(`/admin` → "Token erstellen"). Tick **"Admin (Schreibrechte)"** for a token that
may use the write endpoints; leave it unticked for a read-only token. The full
token is shown **once** in the form `<id>.<secret>`. Send it on every request in
the `X-API-Token` header:

```
X-API-Token: 3.kJ8s2...secret...
```

Tokens are stored only as a salted hash in the database and can be deactivated
in the admin dashboard. A read token on a write endpoint is rejected with `403`.

## Endpoints

### Read (any active token)

| Method | Endpoint | Auth | Description |
| ------ | -------- | ---- | ----------- |
| `GET`  | `/api/v1/health` | none | Liveness probe (`{"status":"ok"}`) |
| `GET`  | `/api/v1/products` | token | List products; supports `?q=` and `?category=` filters |
| `GET`  | `/api/v1/products/<id>` | token | Single product incl. reviews |
| `GET`  | `/api/v1/full` | token | Full export (products + reviews + source requests) |

### Write (admin-scoped token)

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| `POST`   | `/api/v1/products` | Create a product (`name` required, `category` defaults to `Disc`) |
| `PATCH`  | `/api/v1/products/<id>` | Update a product |
| `DELETE` | `/api/v1/products/<id>` | Delete a product |
| `POST`   | `/api/v1/sources` | Create a source request |
| `PATCH`  | `/api/v1/sources/<id>` | Update a source's status (`open`/`approved`/`rejected`) |
| `POST`   | `/api/v1/sources/<id>/scan` | Scan an approved source → `{found, created, duplicates}` |
| `POST`   | `/api/v1/products/<id>/reviews` | Create/update the token owner's review |

Error responses (JSON): `401` missing/invalid token, `403` read token on a write
endpoint, `404` unknown resource, `400` invalid body, `409` scan on a
non-approved source.

## Examples (curl)

```bash
# Health (no token)
curl https://lab10.ifalabs.org/api/v1/health

# List products
curl -H "X-API-Token: 3.kJ8s2..." https://lab10.ifalabs.org/api/v1/products

# Filtered list
curl -H "X-API-Token: 3.kJ8s2..." "https://lab10.ifalabs.org/api/v1/products?q=destroyer"

# Single product
curl -H "X-API-Token: 3.kJ8s2..." https://lab10.ifalabs.org/api/v1/products/1

# Create a product (admin token)
curl -X POST https://lab10.ifalabs.org/api/v1/products \
  -H "X-API-Token: 4.adminSecret..." -H "Content-Type: application/json" \
  -d '{"name":"Wraith","manufacturer":"Innova","speed":11,"glide":5,"turn":-1,"fade":3}'
```

## Examples (HTTPie)

```bash
http GET https://lab10.ifalabs.org/api/v1/products X-API-Token:3.kJ8s2...
```

## Automated smoke test

`scripts/test_api_login.sh` runs the health check, verifies that an
unauthenticated request is rejected with `401`, and — if `API_TOKEN` is set —
exercises the authenticated endpoints:

```bash
chmod +x scripts/test_api_login.sh
API_TOKEN="3.kJ8s2..." ./scripts/test_api_login.sh https://lab10.ifalabs.org
```
