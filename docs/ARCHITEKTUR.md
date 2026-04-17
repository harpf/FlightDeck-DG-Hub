# ClubCore – Architektur & Begründung

## 1. Zielbild

ClubCore ist als **klassische 3-Schichten-Webanwendung** aufgebaut:

1. **Präsentation**: Browser + Jinja2/Bootstrap UI
2. **Anwendung**: Flask-App (Business-Logik, Auth, CRUD, API)
3. **Datenhaltung**: MariaDB

Im Betrieb wird davor ein **Nginx Reverse Proxy** gesetzt, der TLS terminiert und Requests an Flask weiterleitet.

---

## 2. Komponenten und Verantwortlichkeiten

## 2.1 Browser / Frontend
- Serverseitig gerenderte Templates (`app/templates/*`).
- Vorteil: geringe Frontend-Komplexität, schneller Projektstart, einfaches Hosting.

## 2.2 Nginx (`nginx`-Container)
- TLS-Terminierung (HTTPS).
- HTTP → HTTPS Redirect.
- Reverse Proxy auf `app:5000`.
- Begründung: stabile und performante Standard-Lösung für TLS, Caching/Compression später leicht erweiterbar.

## 2.3 Flask-App (`app`-Container)
- Blueprints für Auth, Members, Roles, Events, API.
- Flask-Login für Session-Auth.
- Flask-WTF für Validierung/CSRF-Schutz.
- SQLAlchemy ORM für Datenzugriff.
- Begründung: schnelle Entwicklung, gute Erweiterbarkeit, große Community.

## 2.4 Datenbank (`db`-Container)
- MariaDB als persistente relationale Datenhaltung.
- Persistenz via Docker Volume (`db_data`).
- Begründung: robust für transaktionale CRUD-Workloads und gut mit SQLAlchemy kombinierbar.

## 2.5 Certbot (`certbot`-Container)
- Zertifikatsausstellung und -erneuerung für Let’s Encrypt.
- Begründung: Standardweg für kostenfreie TLS-Zertifikate mit automatisierbarer Renewal-Strategie.

---

## 3. Laufzeitfluss (Request Flow)

1. Client sendet Request an `https://<domain>`.
2. Nginx nimmt TLS entgegen und leitet intern an Flask weiter.
3. Flask verarbeitet Route, Auth, Business-Regeln.
4. SQLAlchemy liest/schreibt MariaDB.
5. Flask rendert HTML oder liefert JSON.
6. Nginx liefert Response an den Browser.

---

## 4. Sicherheits- und Betriebsprinzipien

- Keine öffentliche Registrierung, nur Admin-basierte Benutzeranlage.
- Zugriffsschutz via Login + `admin_required` für schreibende Aktionen.
- CSRF-Schutz durch Flask-WTF.
- Trennung der Infrastruktur in dedizierte Container.

---

## 5. Performance-Betrachtung (aktueller Stand)

Aktuell bereits umgesetzt:

- **DB-Connection-Pooling** über SQLAlchemy Engine Optionen:
  - `pool_pre_ping=True`
  - `pool_recycle`
  - `pool_size`
  - `max_overflow`
- **Indizes auf häufig genutzten Spalten** (z. B. `Member.last_name`, `Member.status`, `Event.event_date`).

Warum das hilft:

- Pooling reduziert Verbindungsaufbaukosten und stabilisiert Lastspitzen.
- Indizes beschleunigen typische Listen-, Filter- und Sortierabfragen.

---

## 6. Konkrete nächste Optimierungen (Roadmap)

## 6.1 App/Backend
- Gunicorn-Tuning pro CPU (`workers`, `threads`, `timeout`, `max-requests`).
- Pagination für große Tabellen (Members/Events).
- Selektives eager loading (`joinedload`) für N+1-Vermeidung.
- Read-heavy Endpunkte mit kurzem Cache (z. B. Dashboard).

## 6.2 Datenbank
- EXPLAIN-Analyse für häufige Queries.
- Composite-Index für kombinierte Filter (z. B. `status + last_name`).
- Geplante Bereinigung/Archivierung historischer Daten.

## 6.3 Nginx
- gzip/brotli aktivieren.
- Statische Assets mit Cache-Control ausliefern.
- Upstream Keepalive und Timeouts feinjustieren.

## 6.4 Betrieb/Monitoring
- Healthchecks in `docker-compose.yml`.
- Metriken + Logs zentralisieren (Prometheus/Grafana, Loki/ELK).
- Alerting bei Container-Neustarts, DB-Verbindungen, 5xx-Rate.

---

## 7. Skalierungsstrategie

Kurzfristig (vertikal):
- Mehr CPU/RAM, Gunicorn-Worker hochsetzen, DB-Parameter feinjustieren.

Mittelfristig (horizontal):
- Flask-App mehrfach replizieren.
- Nginx bzw. Load Balancer vor mehreren App-Instanzen.
- Sessions entweder sticky oder serverseitig (Redis) verwalten.

Langfristig:
- Optional Trennung in API + Frontend.
- Background Jobs (z. B. Mail, Exporte) über Queue (Celery/RQ).

---

## 8. Entscheidungsfazit

Die aktuelle Architektur ist bewusst **einfach, robust und produktionsnah** gewählt:

- schnell deploybar,
- gut wartbar,
- für kleine bis mittlere Vereinsgrößen ausreichend performant,
- und mit klaren Entwicklungspfaden für zukünftige Laststeigerung.
