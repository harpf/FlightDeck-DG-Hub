# ClubCore

ClubCore ist eine webbasierte Vereins- und Mitgliederverwaltung mit Flask, SQLAlchemy, MariaDB und Docker.

## Features

- Login mit `Flask-Login` (keine öffentliche Registrierung)
- Admin-geschützte CRUD-Bereiche für:
  - Mitglieder
  - Rollen/Funktionen
  - Events
- Dashboard mit Kennzahlen (Mitglieder, aktive Mitglieder, kommende Events)
- Readonly-API:
  - `GET /api/members`
  - `GET /api/events`
- Fehlerseiten (403/404/500)
- Reverse Proxy mit Nginx inkl. HTTPS-Weiterleitung und Let's-Encrypt-Struktur

## Projektstruktur

```text
app/
 ├─ templates/
 ├─ __init__.py
 ├─ extensions.py
 ├─ forms.py
 ├─ models.py
 └─ routes.py
config.py
run.py
requirements.txt
Dockerfile
docker-compose.yml
nginx/conf.d/clubcore.conf
```

## Schnellstart (Docker)

1. Umgebungsdatei erstellen:
   ```bash
   cp .env.example .env
   ```
2. Container starten:
   ```bash
   docker compose up -d --build
   ```
3. Migrationen durchführen:
   ```bash
   docker compose exec app flask db init
   docker compose exec app flask db migrate -m "initial"
   docker compose exec app flask db upgrade
   ```
4. Standard-Admin erstellen:
   ```bash
   docker compose exec app flask create-admin
   ```
   Standard-Zugangsdaten: `admin / admin1234`

## HTTPS / Let's Encrypt (Beispiel)

Erstzertifikat anfordern (Domains anpassen):

```bash
docker compose run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d server.domain.tld -d verein.domain.tld \
  --email admin@domain.tld --agree-tos --no-eff-email
```

Danach Nginx neu laden:

```bash
docker compose exec nginx nginx -s reload
```

## Lokaler Dev-Start ohne Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=run.py
flask run --host 0.0.0.0 --port 5000
```

## Testideen

- Login mit Admin-Daten
- Member CRUD (Erstellen, Bearbeiten, Deaktivieren)
- Rollen CRUD
- Event CRUD
- API-Endpunkte mit Login-Session
- Persistenz via `db_data` Volume
- HTTPS und Alias-Domain über Nginx
