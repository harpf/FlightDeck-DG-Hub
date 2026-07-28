# FlightDeck DG Hub – Architektur & Begründung

> Diese Datei beschreibt die **tatsächlich implementierte** Architektur. Punkte,
> die noch nicht umgesetzt sind, stehen klar getrennt unter „Roadmap“.

## 1. Zielbild

FlightDeck DG Hub ist eine Disc-Golf-Wissensplattform und als klassische
**3-Schichten-Webanwendung** aufgebaut:

1. **Präsentation** – serverseitig gerenderte Jinja2-Templates + Bootstrap 5
2. **Anwendung** – Flask-App (Auth, CRUD, Geschäftslogik, REST-API)
3. **Datenhaltung** – MariaDB (relationale Datenbank)

Im Produktionsbetrieb terminiert ein **Nginx Reverse Proxy** TLS und leitet die
Requests an die per **Gunicorn** betriebene Flask-App weiter.

```
Browser / API-Client
        │  HTTPS
        ▼
   ┌─────────┐      ┌──────────────────┐      ┌──────────┐
   │  Nginx  │ ───► │ Gunicorn + Flask │ ───► │ MariaDB  │
   │  (TLS)  │      │   (app:5000)     │      │ (db:3306)│
   └─────────┘      └──────────────────┘      └──────────┘
```

## 2. Komponenten und Verantwortlichkeiten

### 2.1 Browser / Frontend
- Serverseitig gerenderte Templates (`app/templates/*`), Bootstrap über CDN.
- Vorteil: geringe Frontend-Komplexität, schneller Projektstart, einfaches Hosting.

### 2.2 Nginx (`nginx`-Container)
- TLS-Terminierung (HTTPS), HTTP→HTTPS-Redirect, Reverse Proxy auf `app:5000`.
- Konfiguration als Template (`nginx/templates/flightdeck.conf.template`), das
  beim Start per `envsubst` mit Domain/Zertifikatsnamen befüllt wird.
- Begründung: bewährte, performante Standardlösung für TLS; Caching/Compression
  später leicht ergänzbar.

### 2.3 Flask-App (`app`-Container)
- **Blueprints**: `main` (öffentliche Liste/Datenschutz), `auth` (Login/Register),
  `products` (CRUD, Reviews, Source-Anfragen), `admin` (Moderation, Token),
  `api` (REST-API). Siehe `app/routes.py`.
- **Flask-Login** für Session-Authentifizierung.
- **Flask-WTF** für Formularvalidierung und CSRF-Schutz.
- **SQLAlchemy ORM** + **Flask-Migrate** für Datenzugriff und Schemamigrationen.
- Betrieb über **Gunicorn** (`2 workers`, `4 threads`, siehe `Dockerfile`).
- Begründung: schnelle Entwicklung, große Community, gute Erweiterbarkeit.

### 2.4 Datenbank (`db`-Container)
- MariaDB 11.4 als persistente relationale Datenhaltung.
- Persistenz über Docker-Volume `db_data`.
- Begründung: robust für transaktionale CRUD-Workloads, gut mit SQLAlchemy
  kombinierbar.

## 3. Datenmodell

Tabellen (siehe `app/models.py`):

- **User** – Benutzerkonto (eindeutiger `username` + `email`, gehashtes
  Passwort, `is_admin`, `privacy_consent`).
- **Product** – Disc/Produkt mit Disc-Golf-Flugwerten (`speed`, `glide`,
  `turn`, `fade`) und weiteren, vom Crawler befüllten Attributen (`disc_type`,
  `image_url`, `price`, `weight_range_g`, `stability`, …).
- **ProductReview** – Bewertung (1–5) + Kommentar; `UniqueConstraint` auf
  (`user_id`, `product_id`): **eine** Bewertung pro Benutzer und Produkt.
- **SourceRequest** – Benutzer-Anfrage, eine externe Quelle zu scannen;
  Status `open` / `approved` / `rejected`.
- **ApiToken** – API-Zugangstoken (nur Hash gespeichert), aktiv/deaktivierbar;
  `is_admin` trennt lesende von schreibenden Tokens.

Beziehungen: `User 1—* ProductReview *—1 Product`,
`User 1—* SourceRequest`, `User 1—* ApiToken`.

## 4. Geschäftslogik (Auswahl)

- **Suche & Filter** der Produkte nach Freitext (`q`) und Kategorie.
- **Review-Logik**: Upsert pro (User, Produkt) – verhindert Mehrfachbewertungen.
- **Web-Crawler** (`app/scanner.py`): Nur **freigegebene** Quellen werden
  gescannt; vorher wird `robots.txt` geprüft (`is_scraping_allowed`) und ein
  Crawl-/Politeness-Delay eingehalten. Einzelproduktseiten werden direkt aus
  `application/ld+json`-`Product`-Markup ausgelesen; Kategorie-/Listenseiten
  werden über ihre Produktlinks und Paginierung durchsucht (WooCommerce + generische
  Heuristik), mit Retry und Mengenlimits. Duplikate (Name + Hersteller) werden
  übersprungen. Gemeinsame Import-Logik liegt in `app/services.py`.
- **Flugkurven-Diagramm** (`app/flightchart.py`): serverseitiges Inline-SVG aus
  Turn/Fade (kein JavaScript).
- **REST-API** (`/api/v1/*`): lesender Zugriff mit Token-Authentifizierung;
  schreibender Zugriff (Produkte/Quellen/Scan/Reviews) nur mit Admin-Token.

## 5. Sicherheits- und Betriebsprinzipien (implementiert)

- **CSRF-Schutz** über Flask-WTF auf allen Formularen.
- **Security-Header** (`app/__init__.py`): `X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy`, `Content-Security-Policy`.
- **Passwort-Hashing** (`werkzeug.security`), API-Token nur als Hash gespeichert.
- **Cookie-Hardening**: `HttpOnly`, `SameSite=Lax`, `Secure` optional über
  `COOKIE_SECURE`.
- **Zugriffsschutz**: Login-Pflicht für schreibende Aktionen, `admin_required`
  für Admin-Funktionen, Token-Pflicht für die Daten-Endpunkte des API,
  **Admin-Token-Scope** (`is_admin`) für die schreibenden API-Endpunkte (`403`
  für reine Read-Tokens).
- **TLS**: vertrauenswürdiges Let's-Encrypt-Zertifikat (certbot, HTTP-01);
  serverseitig gerendertes SVG wird über `markupsafe` escaped.
- **Container-Hardening**: `no-new-privileges`, `read_only`-Rootfs für app/nginx,
  dedizierter Non-Root-User im Image.
- **Datenschutz**: explizite Einwilligung bei der Registrierung, Datenschutzseite.

## 6. Request Flow

1. Client → `https://<domain>`.
2. Nginx terminiert TLS, leitet intern an Gunicorn/Flask weiter.
3. Flask verarbeitet Route, Auth, Geschäftsregeln.
4. SQLAlchemy liest/schreibt MariaDB.
5. Flask rendert HTML **oder** liefert JSON (API).
6. Nginx liefert die Response an den Client.

## 7. Wartbarkeit, Skalierbarkeit, Verfügbarkeit

**Wartbarkeit**
- Klare Blueprint-Trennung, ORM statt Roh-SQL, zentrale Serializer für das API.
- Automatisierte Tests (`tests/`, pytest) und Schemamigrationen (Flask-Migrate).

**Skalierbarkeit**
- Vertikal: Gunicorn-Worker/Threads erhöhen, DB-Ressourcen anheben.
- Horizontal: App-Container hinter Nginx/Load-Balancer replizieren; Sessions
  serverseitig (z. B. Redis) auslagern.

**Verfügbarkeit**
- `restart: unless-stopped` für alle Container.
- Zustand ausschließlich in MariaDB (Volume) → App-Container sind ersetzbar.
- Public Health-Endpoint `/api/v1/health` für Monitoring/Healthchecks.

## 8. Roadmap (noch NICHT implementiert)

- DB-Connection-Pooling-Tuning (`pool_pre_ping`, `pool_recycle`, `pool_size`).
- Gezielte Indizes nach `EXPLAIN`-Analyse häufiger Queries.
- Pagination für große Produktlisten, `joinedload` gegen N+1.
- gzip/brotli + Cache-Control für statische Assets in Nginx.
- Healthchecks in `docker-compose.yml`, zentrale Logs/Metriken, Alerting.
- Hintergrundjobs (z. B. Scanning) über Queue (Celery/RQ).

## 9. Entscheidungsfazit

Die Architektur ist bewusst **einfach, robust und produktionsnah** gewählt:
schnell deploybar, gut wartbar, für kleine bis mittlere Last ausreichend
performant – mit klaren Pfaden für spätere Laststeigerung.
