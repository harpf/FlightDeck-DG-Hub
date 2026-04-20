# ClubCore

ClubCore ist eine webbasierte Vereins- und Mitgliederverwaltung mit Flask, SQLAlchemy, MariaDB und Docker.

## Features

- Login mit `Flask-Login` (keine öffentliche Registrierung)
- Admin-geschützte CRUD-Bereiche für:
  - Mitglieder
  - Rollen/Funktionen
  - Events
- Dashboard mit Kennzahlen
  - Mitglieder
  - aktive Mitglieder
  - kommende Events
- Readonly-API:
  - `GET /api/members`
  - `GET /api/events`
- Fehlerseiten (`403`, `404`, `500`)
- Reverse Proxy mit Nginx
- HTTPS-Setup mit Let's Encrypt für produktive Deployments

---

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
docker-compose.override.yml
.env.example
nginx/
 ├─ conf.d/
 └─ templates/
     └─ clubcore.conf.template
certbot/
 ├─ conf/
 └─ www/
```

---

## Voraussetzungen

Für die Entwicklung in einer Ubuntu-VM werden empfohlen:

- Ubuntu VM
- Git
- Docker Engine
- Docker Compose Plugin
- Visual Studio Code
- VS Code Extension `Dev Containers`
- VS Code Extension `Python`
- VS Code Extension `Pylance`

---

## Initialsetup unter Ubuntu

### System aktualisieren

```bash
sudo apt update
sudo apt upgrade -y
```

### Grundlegende Pakete installieren

```bash
sudo apt install -y git ca-certificates curl gnupg wget
```

### Alte Docker-Pakete entfernen

```bash
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do
  sudo apt remove -y $pkg
done
```

### Docker-Repository einrichten

```bash
sudo install -m 0755 -d /etc/apt/keyrings

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

### Docker Engine und Compose Plugin installieren

```bash
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### VS Code installieren

```bash
wget -O code.deb "https://code.visualstudio.com/sha/download?build=stable&os=linux-deb-x64"
sudo apt install -y ./code.deb
rm code.deb
```

### Benutzer zur Docker-Gruppe hinzufügen

```bash
sudo usermod -aG docker $USER
newgrp docker
```

> Falls `docker ps` danach noch nicht ohne `sudo` funktioniert, bitte einmal ab- und wieder anmelden oder die VM neu starten.

### VS Code Extensions installieren

```bash
code --install-extension ms-vscode-remote.remote-containers
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
```

### Installation prüfen

```bash
git --version
docker --version
docker compose version
code --version
```

---

## Repository klonen

Es wird empfohlen, das Projekt im Home-Verzeichnis abzulegen, z. B. unter `~/projects`.

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/harpf/ClubCore.git
cd ClubCore
```

---

## Umgebungsdatei anlegen

```bash
cp .env.example .env
```

### Beispiel für `.env.example`

```env
SECRET_KEY=change-me
DATABASE_URL=mysql+pymysql://clubcore:clubcore@db:3306/clubcore

DOMAIN=verein.example.com
ALT_DOMAIN=www.verein.example.com
CERT_NAME=verein.example.com
LETSENCRYPT_EMAIL=admin@example.com

MARIADB_DATABASE=clubcore
MARIADB_USER=clubcore
MARIADB_PASSWORD=clubcore
MARIADB_ROOT_PASSWORD=rootsecret
```

### Bedeutung der HTTPS-Variablen

- `DOMAIN`: Hauptdomain der Anwendung
- `ALT_DOMAIN`: zusätzliche Domain, z. B. `www`
- `CERT_NAME`: Verzeichnisname des Zertifikats unter `/etc/letsencrypt/live/...`
- `LETSENCRYPT_EMAIL`: E-Mail-Adresse für Let's Encrypt

> `CERT_NAME` sollte normalerweise der Hauptdomain entsprechen, z. B. `verein.example.com`.

---

# Entwicklung mit Docker (empfohlen)

Für die lokale Entwicklung wird eine zusätzliche Datei `docker-compose.override.yml` verwendet.  
Damit wird:

- der Quellcode ins laufende App-Container-Dateisystem gemountet
- Flask im Debug-Modus gestartet
- der Zugriff direkt auf Port `5000` ermöglicht
- `nginx` für die lokale Entwicklung deaktiviert

## `docker-compose.override.yml`

```yaml
services:
  app:
    volumes:
      - ./:/app
    environment:
      FLASK_APP: run.py
      FLASK_ENV: development
      FLASK_DEBUG: "1"
    command: flask run --host=0.0.0.0 --port=5000 --debug
    ports:
      - "5000:5000"

  nginx:
    profiles: ["prod"]
```

> Hinweis: Diese Override-Datei ist für die **lokale Entwicklung** gedacht.  
> Das produktive HTTPS-Setup erfolgt weiterhin über das normale `docker-compose.yml` zusammen mit Nginx und Certbot.

---

## Lokaler Docker-Start mit Override

### Container bauen und starten

```bash
docker compose up -d --build
```

### Datenbankmigrationen ausführen

Beim ersten Start:

```bash
docker compose exec app flask db init
docker compose exec app flask db migrate -m "initial"
docker compose exec app flask db upgrade
```

> `flask db init` muss nur **einmal** ausgeführt werden.  
> Bei späteren Model-Änderungen reichen normalerweise:

```bash
docker compose exec app flask db migrate -m "describe change"
docker compose exec app flask db upgrade
```

### Standard-Admin erstellen

```bash
docker compose exec app flask create-admin
```

Standard-Zugangsdaten:

```text
Benutzername: admin
Passwort:     admin1234
```

### Anwendung aufrufen

Lokal in der VM:

```text
http://localhost:5000
```

Von außerhalb der VM:

```text
http://<IP-DER-VM>:5000
```

---

## Logs und Diagnose

Alle Logs:

```bash
docker compose logs -f
```

Nur App-Logs:

```bash
docker compose logs -f app
```

Nur Datenbank-Logs:

```bash
docker compose logs -f db
```

Nur Nginx-Logs:

```bash
docker compose logs -f nginx
```

Container-Status prüfen:

```bash
docker compose ps
docker ps
```

---

## Typischer Entwicklungsworkflow

### Projekt in VS Code öffnen

```bash
code .
```

### Änderungen am Code

Durch das Volume-Mounting in der `docker-compose.override.yml` werden Änderungen direkt aus dem Projektordner in den Container gespiegelt.

### Container neu bauen

Falls sich Abhängigkeiten geändert haben oder der Build aktualisiert werden muss:

```bash
docker compose down
docker compose up -d --build
```

### Komplett neu starten

Wenn du die Datenbank zurücksetzen möchtest:

```bash
docker compose down -v
docker compose up -d --build
```

> Achtung: `-v` entfernt auch persistente Volumes wie `db_data`.

---

# Produktivbetrieb mit HTTPS

Für ein korrektes HTTPS-Setup wird **ohne lokales Dev-Override** gearbeitet.  
Dabei übernimmt `nginx` den Reverse Proxy und nutzt Zertifikate von Let's Encrypt.

## Wichtiger Hinweis

Das HTTPS-Setup verwendet:

- ein Nginx-Template mit Platzhaltern aus der `.env`
- `envsubst` beim Start des Nginx-Containers
- einen `init-letsencrypt`-Container, der beim ersten Start ein temporäres Dummy-Zertifikat erzeugt

Dadurch kann `nginx` bereits starten, **bevor** das erste echte Let's-Encrypt-Zertifikat vorhanden ist.

---

## Produktives `docker-compose.yml`

```yaml
services:
  app:
    build: .
    container_name: clubcore_app
    env_file:
      - .env
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: mariadb:11.4
    container_name: clubcore_db
    restart: unless-stopped
    environment:
      MARIADB_DATABASE: ${MARIADB_DATABASE}
      MARIADB_USER: ${MARIADB_USER}
      MARIADB_PASSWORD: ${MARIADB_PASSWORD}
      MARIADB_ROOT_PASSWORD: ${MARIADB_ROOT_PASSWORD}
    volumes:
      - db_data:/var/lib/mysql

  init-letsencrypt:
    image: alpine:3.20
    container_name: clubcore_init_letsencrypt
    env_file:
      - .env
    volumes:
      - ./certbot/conf:/etc/letsencrypt
    command: >
      sh -c "
      apk add --no-cache openssl &&
      mkdir -p /etc/letsencrypt/live/${CERT_NAME} &&
      if [ ! -f /etc/letsencrypt/live/${CERT_NAME}/fullchain.pem ] || [ ! -f /etc/letsencrypt/live/${CERT_NAME}/privkey.pem ]; then
        openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
          -keyout /etc/letsencrypt/live/${CERT_NAME}/privkey.pem \
          -out /etc/letsencrypt/live/${CERT_NAME}/fullchain.pem \
          -subj '/CN=${CERT_NAME}';
      fi
      "

  nginx:
    image: nginx:1.27-alpine
    container_name: clubcore_nginx
    depends_on:
      app:
        condition: service_started
      init-letsencrypt:
        condition: service_completed_successfully
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/templates:/etc/nginx/templates:ro
      - ./certbot/www:/var/www/certbot:ro
      - ./certbot/conf:/etc/letsencrypt:ro
    environment:
      DOMAIN: ${DOMAIN}
      ALT_DOMAIN: ${ALT_DOMAIN}
      CERT_NAME: ${CERT_NAME}
    command: >
      /bin/sh -c "
      envsubst '\$DOMAIN \$ALT_DOMAIN \$CERT_NAME' \
      < /etc/nginx/templates/clubcore.conf.template \
      > /etc/nginx/conf.d/default.conf &&
      nginx -g 'daemon off;'
      "
    restart: unless-stopped

  certbot:
    image: certbot/certbot:latest
    container_name: clubcore_certbot
    env_file:
      - .env
    volumes:
      - ./certbot/www:/var/www/certbot
      - ./certbot/conf:/etc/letsencrypt
    entrypoint: /bin/sh
    command: -c "trap exit TERM; while :; do sleep 12h & wait $${!}; certbot renew --webroot -w /var/www/certbot; done"

volumes:
  db_data:
```

---

## Nginx-Template

Pfad:

```text
nginx/templates/clubcore.conf.template
```

Inhalt:

```nginx
server {
    listen 80;
    server_name ${DOMAIN} ${ALT_DOMAIN};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name ${DOMAIN} ${ALT_DOMAIN};

    ssl_certificate /etc/letsencrypt/live/${CERT_NAME}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${CERT_NAME}/privkey.pem;

    location / {
        proxy_pass http://app:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Warum ein Template?

Docker Compose kann Variablen aus `.env` direkt in `docker-compose.yml` ersetzen.  
Nginx liest diese `.env`-Variablen aber nicht automatisch in statischen Konfigurationsdateien.

Deshalb wird beim Start des Nginx-Containers die fertige Konfiguration aus einem Template erzeugt.

---

## Voraussetzungen für HTTPS

Vor dem Zertifikatsbezug müssen:

- Domain(s) korrekt auf den Server zeigen
- Port `80` und `443` erreichbar sein
- die `.env` korrekt gepflegt sein
- das Nginx-Template vorhanden sein

Beispiel:

```env
DOMAIN=verein.example.com
ALT_DOMAIN=www.verein.example.com
CERT_NAME=verein.example.com
LETSENCRYPT_EMAIL=admin@example.com
```

---

## Erststart mit HTTPS

### Container starten

```bash
docker compose -f docker-compose.yml up -d --build
```

Beim ersten Start wird durch `init-letsencrypt` ein temporäres Zertifikat erzeugt, damit `nginx` hochfahren kann.

### Echtes Let's-Encrypt-Zertifikat anfordern

```bash
docker compose run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d "$DOMAIN" -d "$ALT_DOMAIN" \
  --email "$LETSENCRYPT_EMAIL" \
  --agree-tos --no-eff-email
```

### Nginx neu laden

```bash
docker compose exec nginx nginx -s reload
```

Danach sollte `nginx` das echte Zertifikat verwenden.

---

## Zertifikatserneuerung

Der `certbot`-Container versucht regelmäßig eine Erneuerung auszuführen:

```text
certbot renew --webroot -w /var/www/certbot
```

Falls ein Zertifikat erneuert wurde, sollte `nginx` anschließend neu geladen werden:

```bash
docker compose exec nginx nginx -s reload
```

---

## HTTPS prüfen

Nach erfolgreichem Zertifikatsbezug und Start von Nginx sollte die Anwendung über HTTPS erreichbar sein:

```text
https://verein.example.com
```

---

## Unterschied zwischen Development und Production

### Development ohne HTTPS

Verwendet automatisch:

- `docker-compose.yml`
- `docker-compose.override.yml`

Start:

```bash
docker compose up -d --build
```

Zugriff:

```text
http://localhost:5000
```

### Production mit HTTPS

Verwendet nur:

- `docker-compose.yml`

Start:

```bash
docker compose -f docker-compose.yml up -d --build
```

Zugriff:

```text
https://<deine-domain>
```

---

## Lokaler Dev-Start ohne Docker

Alternativ kann ClubCore auch direkt lokal mit Python gestartet werden:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=run.py
flask run --host 0.0.0.0 --port 5000
```

---

## Testideen

- Login mit Admin-Daten
- Member CRUD
  - Erstellen
  - Bearbeiten
  - Deaktivieren
- Rollen CRUD
- Event CRUD
- API-Endpunkte mit Login-Session
- Persistenz via `db_data` Volume
- Nginx Reverse Proxy
- HTTPS mit Let's Encrypt
- Verhalten im lokalen Dev-Modus über Port `5000`

---

## Troubleshooting

### `docker` funktioniert nur mit `sudo`

Benutzer zur Docker-Gruppe hinzufügen:

```bash
sudo usermod -aG docker $USER
newgrp docker
```

Danach ggf. ab- und wieder anmelden oder die VM neu starten.

---

### `nginx` startet nicht

Wenn im Log Fehler wie die folgenden erscheinen:

```text
cannot load certificate
/etc/letsencrypt/live/...
```

dann fehlen Zertifikate oder `CERT_NAME` passt nicht zum tatsächlichen Zertifikatspfad.

Prüfen:

- existiert `./certbot/conf/live/${CERT_NAME}/fullchain.pem`
- existiert `./certbot/conf/live/${CERT_NAME}/privkey.pem`
- stimmt `CERT_NAME` in der `.env`
- ist das Nginx-Template korrekt

Für die lokale Entwicklung:

- `docker-compose.override.yml` verwenden
- direkt auf `http://localhost:5000` gehen
- `nginx` nicht lokal erzwingen

---

### Die App läuft, ist aber im Browser nicht erreichbar

Prüfen:

```bash
docker compose ps
docker compose logs -f app
ss -tulpn | grep 5000
```

Im Dev-Setup muss Port `5000` gemappt sein:

```yaml
ports:
  - "5000:5000"
```

Im HTTPS-Setup zusätzlich prüfen:

```bash
docker compose logs -f nginx
```

---

### Certbot kann kein Zertifikat holen

Prüfen:

- zeigen `DOMAIN` und `ALT_DOMAIN` auf den Server?
- ist Port `80` öffentlich erreichbar?
- wird `/.well-known/acme-challenge/` korrekt ausgeliefert?
- ist `LETSENCRYPT_EMAIL` gesetzt?

---

### Migration schlägt fehl

Beim ersten Start:

```bash
docker compose exec app flask db init
docker compose exec app flask db migrate -m "initial"
docker compose exec app flask db upgrade
```

Bei späteren Änderungen nicht erneut `flask db init` ausführen.

---

## Empfehlung für die Entwicklung

Für die tägliche Entwicklung in einer Ubuntu-VM wird empfohlen:

- Projekt unter `~/projects/ClubCore`
- Entwicklung mit `docker-compose.override.yml`
- Zugriff direkt über `http://localhost:5000`
- Nutzung von VS Code + Dev Containers / Python Extension
- Nginx + HTTPS nur für produktionsnahe Tests oder Deployment
