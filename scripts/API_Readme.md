# FlightDeck DG Hub — Web-API

A read-only RESTful Web-API for selected application data (disc/products,
reviews, source requests). It is consumable with any HTTP client (curl, HTTPie,
Postman) **without a browser**.

## Interactive documentation (Swagger UI)

- **Swagger UI:** `GET /api/docs` — browse and "Try it out" against the live API
  (click *Authorize* and paste an `<id>.<secret>` token).
- **OpenAPI spec:** `GET /api/openapi.json` — the machine-readable OpenAPI 3.0
  document (also importable into Postman/Insomnia).

## Authentication

The API uses a **static API token**. An admin creates a token in the web UI
(`/admin` → "Token erstellen"). The full token is shown **once** in the form
`<id>.<secret>`. Send it on every request in the `X-API-Token` header:

```
X-API-Token: 3.kJ8s2...secret...
```

Tokens are stored only as a salted hash in the database and can be deactivated
in the admin dashboard.

## Endpoints

| Method | Endpoint | Auth | Description |
| ------ | -------- | ---- | ----------- |
| `GET`  | `/api/v1/health` | none | Liveness probe (`{"status":"ok"}`) |
| `GET`  | `/api/v1/products` | token | List products; supports `?q=` and `?category=` filters |
| `GET`  | `/api/v1/products/<id>` | token | Single product incl. reviews |
| `GET`  | `/api/v1/full` | token | Full export (products + reviews + source requests) |

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
