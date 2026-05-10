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
- `GET /api/v1/full` (Token erforderlich via `X-API-Token`)

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
