# FlightDeck DG Hub

FlightDeck DG Hub ist eine DiscGolf-Wissensplattform mit Flask, MariaDB und Docker Compose.

**Live:** https://lab10.ifalabs.org (HTTPS, Let's-Encrypt-Zertifikat) ·
**Repository:** https://github.com/harpf/FlightDeck-DG-Hub

## Features
- Produktkatalog mit Freitextsuche, Kategorie-Filter und Bewertungen
- **Web-Crawler**: importiert Discs aus freigegebenen Shop-Quellen (schema.org-JSON-LD,
  folgt Kategorieseiten inkl. Paginierung, respektiert `robots.txt` + Crawl-Delay);
  extrahiert Flugwerte, Preis, Gewicht, Stability und Produktbild
- **Flugkurven-Diagramm** je Disc, serverseitig aus Turn/Fade als Inline-SVG gerendert
- **E-Mail-Flows** (Postfix): Registrierungsbestätigung, Passwort-Reset, Admin-Testmail
- **REST-API** (lesend + Admin-Token-Schreibzugriff) mit Swagger-UI
- Betrieb via Docker Compose hinter Nginx + Gunicorn, HTTPS über Let's Encrypt,
  CI/CD-Deploy via GitHub Actions

## Rollen
- **Anonym:** Produkte ansehen, filtern, suchen
- **User:** Produkte erstellen, bewerten, Source-Anfragen senden
- **Admin:** Source-Anfragen moderieren + Quellen scannen, Benutzer aktivieren/deaktivieren,
  API-Tokens (lesend/Admin) verwalten

## Sicherheit & Datenschutz
- HTTPS mit vertrauenswürdigem Let's-Encrypt-Zertifikat
- E-Mail-Bestätigung bei der Registrierung, Passwort-Reset per Token
- CSRF-Schutz über Flask-WTF
- Sicherheitsheader (CSP, Frame/Type/Referrer Policy)
- Gehashte Passwörter (scrypt) und API-Tokens; Admin-Scope für Schreib-API
- Cookie-Hardening (HttpOnly, SameSite, Secure)
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
Die Plattform läuft mit **Docker + Flask (Gunicorn) + MariaDB + Nginx**.

Lokaler Schnellstart (Dev-Override, HTTP):

```bash
cp .env.example .env    # Secrets setzen
docker compose up -d --build
```

Produktion auf dem Server (HTTPS): siehe [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
– inkl. Let's-Encrypt-Zertifikat (`scripts/renew-cert.sh` für die Erneuerung) und
dem One-Shot-Setup `scripts/server-setup.sh`. Kurzform:

```bash
docker compose -f docker-compose.yml -f docker-compose.tls.yml up -d --build
```

Datenbank migrieren und Admin anlegen:

```bash
docker compose exec app flask db upgrade
BOOTSTRAP_ADMIN_PASSWORD='set-a-strong-secret' docker compose exec app flask create-admin
```
