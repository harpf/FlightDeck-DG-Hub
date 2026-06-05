# Installationsanleitung – FlightDeck DG Hub

Diese Anleitung beschreibt drei Wege, die Anwendung zum Laufen zu bringen:

- **Variante A – Lokale Entwicklung** (Python venv, ohne Docker, SQLite)
- **Variante B – Lokal mit Docker Compose** (wie Produktion, mit MariaDB)
- **Variante C – Produktiver Server** (Linux-Host, HTTPS) → siehe
  [`DEPLOYMENT.md`](DEPLOYMENT.md)

> Schnellster Start zum Ausprobieren: **Variante A**. Für eine
> produktionsnahe Umgebung: **Variante B**.

---

## 1 Voraussetzungen

| Software | Version | Variante |
| --- | --- | --- |
| Python | ≥ 3.9 (getestet 3.12 / 3.14) | A |
| pip / venv | aktuell | A |
| Docker Engine + Compose-Plugin | aktuell | B, C |
| Git | aktuell | alle |

Repository klonen:

```bash
git clone https://github.com/harpf/FlightDeck-DG-Hub.git
cd FlightDeck-DG-Hub
```

---

## 2 Variante A – Lokale Entwicklung (venv + SQLite)

Diese Variante benötigt **keine** Datenbank-Installation: per
`DATABASE_URL` wird SQLite verwendet. Die Anwendung ist DB-unabhängig
(SQLAlchemy-ORM), daher funktioniert derselbe Code später unverändert mit
MariaDB.

### 2.1 Virtuelle Umgebung & Abhängigkeiten

**Windows (PowerShell):**

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### 2.2 Umgebungsvariablen setzen

**Windows (PowerShell):**

```powershell
$env:FLASK_APP = "run.py"
$env:DATABASE_URL = "sqlite:///dev.db"
$env:SECRET_KEY = "dev-secret"
$env:BOOTSTRAP_ADMIN_PASSWORD = "admin12345"
```

**Linux / macOS:**

```bash
export FLASK_APP=run.py
export DATABASE_URL="sqlite:///dev.db"
export SECRET_KEY=dev-secret
export BOOTSTRAP_ADMIN_PASSWORD=admin12345
```

### 2.3 Datenbank initialisieren & Admin anlegen

```bash
flask init-db
flask create-admin
```

### 2.4 Anwendung starten

```bash
flask run --port 5000
```

Aufruf im Browser: <http://localhost:5000/>
API-Health: <http://localhost:5000/api/v1/health>

### 2.5 Tests ausführen (optional, keine DB nötig)

Die Testsuite verwendet eine In-Memory-SQLite-DB (`TestingConfig`):

**Windows:** `.\.venv\Scripts\python.exe -m pytest`
**Linux/macOS:** `pytest`

Erwartet: **26 passed**.

---

## 3 Variante B – Lokal mit Docker Compose (MariaDB)

Diese Variante startet App + MariaDB wie in Produktion. Die mitgelieferte
`docker-compose.override.yml` aktiviert automatisch den Flask-Entwicklungsserver
mit Port 5000.

### 3.1 .env anlegen

```bash
cp .env.example .env
# Werte in .env nach Bedarf anpassen (Passwörter etc.)
```

### 3.2 Container starten

```bash
docker compose up -d --build
```

### 3.3 Schema & Admin

```bash
docker compose exec -e FLASK_APP=run.py app flask init-db
docker compose exec -e FLASK_APP=run.py app flask create-admin
```

### 3.4 Aufruf

<http://localhost:5000/> – die App läuft hinter dem Flask-Dev-Server.

### 3.5 Stoppen

```bash
docker compose down          # Container stoppen (Daten bleiben im Volume)
docker compose down -v       # inkl. Datenbank-Volume löschen
```

---

## 4 Variante C – Produktiver Server (HTTPS)

Für die Bereitstellung über das Internet (Nginx + Gunicorn + MariaDB, mit
TLS) gibt es ein einziges Setup-Skript:

```bash
chmod +x scripts/server-setup.sh
./scripts/server-setup.sh            # self-signed HTTPS, Standard-Domain lab10.ifalabs.org
```

Details, TLS-Modi (`http` / `selfsigned` / `letsencrypt`) und Let's-Encrypt-
Voraussetzungen: siehe [`DEPLOYMENT.md`](DEPLOYMENT.md).

---

## 5 Erste Schritte nach der Installation

1. Im Browser **registrieren** (Benutzername, E-Mail, Passwort ≥ 10 Zeichen).
2. Als `admin` anmelden und unter **/admin** einen **API-Token** erstellen
   (wird nur einmal angezeigt).
3. API testen:
   ```bash
   API_TOKEN="<id>.<secret>" ./scripts/test_api_login.sh http://localhost:5000
   ```

---

## 6 Troubleshooting

| Problem | Ursache / Lösung |
| --- | --- |
| `flask: command not found` | venv nicht aktiviert bzw. unter Windows `.\.venv\Scripts\python.exe -m flask ...` verwenden |
| `Could not locate a Flask application` | `FLASK_APP=run.py` nicht gesetzt |
| DB-Verbindungsfehler (Variante B) | MariaDB-Container noch nicht bereit – kurz warten und Befehl erneut ausführen |
| `pymysql.err.OperationalError` lokal | In Variante A `DATABASE_URL=sqlite:///dev.db` setzen (kein MariaDB nötig) |
| Browser warnt vor Zertifikat (Variante C) | self-signed Zertifikat – für vertrauenswürdiges Zertifikat `TLS_MODE=letsencrypt` nutzen |
| Port 5000 belegt | anderen Port wählen: `flask run --port 5001` |
