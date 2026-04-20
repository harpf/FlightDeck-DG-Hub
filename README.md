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
nginx/conf.d/clubcore.conf
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

Das Standard-Compose mit `nginx` erwartet gültige Zertifikatsdateien.  
Wenn diese nicht vorhanden sind, startet `nginx` nicht.

Für die lokale Entwicklung deshalb bitte das Override-Setup verwenden.  
Für produktive oder servernahe Deployments ist dagegen das vollständige HTTPS-Setup mit Certbot vorgesehen.

---

## Voraussetzungen für HTTPS

Vor dem Zertifikatsbezug müssen:

- Domain(s) korrekt auf den Server zeigen
- Port `80` und `443` erreichbar sein
- Nginx-Konfiguration und Domainnamen korrekt angepasst sein

Beispiel-Domains:

- `server.domain.tld`
- `verein.domain.tld`

---

## HTTPS-Erstzertifikat anfordern

Domains und E-Mail-Adresse anpassen:

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

---

## Produktivstart mit HTTPS

Falls für die Entwicklung ein `docker-compose.override.yml` vorhanden ist, kann es für den produktiven Start ignoriert werden, indem nur das Haupt-Compose verwendet wird oder die Konfiguration entsprechend getrennt wird.

Standardstart:

```bash
docker compose up -d --build
```

Falls das lokale Override aktiv ist und `nginx` auf ein Profil gesetzt wurde, muss `nginx` explizit über das Profil gestartet werden:

```bash
docker compose --profile prod up -d --build
```

> Empfehlung: Für Produktion und Entwicklung getrennte Compose-Dateien oder klar getrennte Profile verwenden.

---

## HTTPS prüfen

Nach erfolgreichem Zertifikatsbezug und Start von Nginx sollte die Anwendung über HTTPS erreichbar sein:

```text
https://verein.domain.tld
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

dann fehlen die TLS-Zertifikate.

Für die lokale Entwicklung:

- `docker-compose.override.yml` verwenden
- direkt auf `http://localhost:5000` gehen
- `nginx` nicht lokal erzwingen

Für HTTPS:

- erst Zertifikate mit Certbot erzeugen
- danach `nginx` neu laden

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
