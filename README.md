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

---

## Vollständige Installationsanleitung (Linux)

Die folgenden Schritte sind für eine frische Linux-VM (z. B. Ubuntu 22.04/24.04) gedacht.

### 1) System vorbereiten

```bash
sudo apt update
sudo apt -y upgrade
sudo apt -y install ca-certificates curl gnupg lsb-release git ufw
```

Optional (empfohlen): Firewall nur für SSH/HTTP/HTTPS öffnen.

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
sudo ufw status
```

### 2) Docker Engine installieren

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo ${VERSION_CODENAME}) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Docker-Dienst aktivieren und testen:

```bash
sudo systemctl enable --now docker
sudo docker run --rm hello-world
```

Optional: Docker ohne `sudo` nutzen (danach einmal neu anmelden):

```bash
sudo usermod -aG docker $USER
newgrp docker
```

### 3) Projekt auf den Server holen

```bash
git clone <DEIN_REPO_URL> ClubCore
cd ClubCore
```

### 4) Compose vorbereiten

Umgebungsvariablen anlegen:

```bash
cp .env.example .env
```

`.env` anpassen (mindestens `SECRET_KEY` setzen):

```dotenv
SECRET_KEY=bitte-einen-langen-zufallswert-nutzen
DATABASE_URL=mysql+pymysql://clubcore:clubcore@db:3306/clubcore
```

### 5) Container mit Docker Compose bauen und starten

```bash
docker compose up -d --build
```

Status prüfen:

```bash
docker compose ps
docker compose logs -f app
```

### 6) Datenbank-Migrationen durchführen

```bash
docker compose exec app flask db init
docker compose exec app flask db migrate -m "initial"
docker compose exec app flask db upgrade
```

### 7) Admin-User erzeugen

```bash
docker compose exec app flask create-admin
```

Standard-Login danach: `admin / admin1234` (bitte direkt ändern).

---

## Let's Encrypt – ist es im Setup eingebunden?

**Kurzantwort:** Ja, **vorbereitet/eingebunden**, aber **nicht vollautomatisch aktiviert**.

### Was bereits vorhanden ist

- `docker-compose.yml` enthält einen `certbot`-Service und die nötigen Volumes.
- Nginx liefert `/.well-known/acme-challenge/` aus.
- Nginx ist auf HTTP→HTTPS Redirect + SSL-Zertifikatpfade konfiguriert.

### Was du noch tun musst

1. In `nginx/conf.d/clubcore.conf` echte Domains eintragen (statt `server.domain.tld` / `verein.domain.tld`).
2. DNS-A/AAAA-Records auf deinen Server zeigen lassen.
3. Zertifikat anfordern.
4. Nginx neu laden.

Beispiel:

```bash
docker compose run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d server.domain.tld -d verein.domain.tld \
  --email admin@domain.tld --agree-tos --no-eff-email

docker compose exec nginx nginx -s reload
```

### Optional: automatische Zertifikatserneuerung

`certbot` regelmäßig ausführen (z. B. per Cron):

```bash
0 3 * * * cd /pfad/zu/ClubCore && docker compose run --rm certbot renew && docker compose exec nginx nginx -s reload
```

---

## Lokaler Dev-Start ohne Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=run.py
flask run --host 0.0.0.0 --port 5000
```


## Architektur-Dokumentation

Eine ausführliche Beschreibung der Systemarchitektur inkl. Begründungen und Performance-Roadmap findest du hier:

- [`docs/ARCHITEKTUR.md`](docs/ARCHITEKTUR.md)

## Häufige Checks

- Erreichbarkeit: `http://<SERVER-IP>`
- Nach Zertifikat: `https://<DEINE-DOMAIN>`
- Container laufen: `docker compose ps`
- DB-Volume persistent: `docker volume ls | grep db_data`

## Testideen

- Login mit Admin-Daten
- Member CRUD (Erstellen, Bearbeiten, Deaktivieren)
- Rollen CRUD
- Event CRUD
- API-Endpunkte mit Login-Session
- Persistenz via `db_data` Volume
- HTTPS und Alias-Domain über Nginx
