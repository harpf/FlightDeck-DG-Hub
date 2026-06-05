# FlightDeck DG Hub

FlightDeck DG Hub ist eine DiscGolf-Wissensplattform mit Flask, MariaDB und Docker Compose.

## Rollen
- **Anonym:** Produkte ansehen, filtern, suchen
- **User:** Produkte erstellen, bewerten, Source-Anfragen senden
- **Admin:** Source-Anfragen moderieren, API-Tokens verwalten

## Sicherheit & Datenschutz
- CSRF-Schutz über Flask-WTF
- Sicherheitsheader (CSP, Frame/Type/Referrer Policy)
- Gehashte API-Tokens
- Cookie-Hardening (HttpOnly, SameSite, optional Secure)
- Datenschutzseite und Einwilligung bei Registrierung

## API
REST-API, Auth über `X-API-Token` (Token im Admin-Dashboard erstellen). Lesende
Endpunkte funktionieren mit jedem Token; **schreibende Endpunkte erfordern einen
Admin-Token** (Checkbox „Admin (Schreibrechte)" beim Erstellen).

Lesend:
- `GET /api/v1/health` (öffentlich)
- `GET /api/v1/products` (Token; `?q=`, `?category=`)
- `GET /api/v1/products/<id>` (Token)
- `GET /api/v1/full` (Token)

Schreibend (Admin-Token):
- `POST /api/v1/products`, `PATCH /api/v1/products/<id>`, `DELETE /api/v1/products/<id>`
- `POST /api/v1/sources`, `PATCH /api/v1/sources/<id>`, `POST /api/v1/sources/<id>/scan`
- `POST /api/v1/products/<id>/reviews`

Interaktive Doku: **Swagger UI** unter `/api/docs` (Spec: `/api/openapi.json`).
Details: [`scripts/API_Readme.md`](scripts/API_Readme.md).

## Tests
```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt
.venv/Scripts/python -m pytest
```

## Dokumentation
- [`docs/INSTALL.md`](docs/INSTALL.md) – Installationsanleitung (lokal & Server)
- [`docs/PRAXISARBEIT.md`](docs/PRAXISARBEIT.md) – Lösungsdokument (Management Summary, User Manual, API, Diagramme, Testprotokoll)
- [`docs/ARCHITEKTUR.md`](docs/ARCHITEKTUR.md) – Architektur & Begründung
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) – Deployment-Anleitung (Lab-VM)

## Docker Compose
Die Plattform läuft weiterhin mit **Docker + Flask + MariaDB**.

```bash
docker compose up -d --build
```

Danach Migrationen anwenden und Admin erstellen:

```bash
docker compose exec app flask db migrate -m "schema updates"
docker compose exec app flask db upgrade
BOOTSTRAP_ADMIN_PASSWORD='set-a-strong-secret' docker compose exec app flask create-admin
```
