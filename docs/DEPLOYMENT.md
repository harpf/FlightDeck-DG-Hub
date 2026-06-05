# Deployment Guide – FlightDeck DG Hub

Target for the exam window: the lab VM **lab10.ifalabs.org** (`34.65.14.54`,
Google Cloud, Zurich). The same steps work on any Linux host with Docker.

> The application must stay reachable for at least 4 weeks during the
> correction period. Use a host that stays online (the GCP lab VM, a VPS, etc.).

---

## 0. Connectivity note

`lab10.ifalabs.org` was **not reachable from the corporate Hirslanden network**
during development (SSH/HTTP/HTTPS timed out). Run the deployment from a network
that can reach the lab — i.e. SSH **into** the VM and run the commands there
(VPN / school network / GCP console SSH).

---

## 1. Connect to the host

```bash
ssh student@lab10.ifalabs.org
```

A deploy SSH key was generated locally during setup
(`~/.ssh/flightdeck_deploy.pub`). Optionally append it to
`~/.ssh/authorized_keys` on the VM for password-less access.

---

## 2. Install Docker (first time only)

```bash
# Docker Engine + compose plugin (Debian/Ubuntu)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"     # log out/in afterwards so docker works rootless
docker --version && docker compose version
```

---

## Quick start — one-shot setup script (recommended)

After cloning the repo on the host, a single script does **everything** below
(installs Docker, generates `.env` secrets, provisions TLS, starts the stack,
creates the schema + admin, smoke-tests):

```bash
cd flightdeck
chmod +x scripts/server-setup.sh

# Self-signed HTTPS (works immediately, no DNS needed) on lab10.ifalabs.org:
./scripts/server-setup.sh

# Trusted HTTPS via Let's Encrypt (requires public DNS A-record + open tcp:80):
DOMAIN=discgolf.ifalabs.org TLS_MODE=letsencrypt LETSENCRYPT_EMAIL=you@ifalabs.org ./scripts/server-setup.sh

# Plain HTTP (no TLS):
TLS_MODE=http ./scripts/server-setup.sh
```

The script prints the generated admin password (also saved in `.env`).

> Want `discgolf.ifalabs.org`? It has **no DNS record yet** — first create an
> A-record `discgolf.ifalabs.org → 34.65.14.54`, then run with
> `TLS_MODE=letsencrypt`. Without DNS, use the default self-signed mode.

The sections below document the same steps manually.

---

## 3. Get the code

```bash
git clone <REPO_URL> flightdeck && cd flightdeck
# later updates:  git pull
```

---

## 4. Configure secrets

```bash
cp .env.example .env
nano .env
```

Set **strong** values for at least:

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Flask session signing — must be random |
| `DATABASE_URL` | `mysql+pymysql://flightdeck:<pw>@db:3306/flightdeck` |
| `MARIADB_PASSWORD` / `MARIADB_ROOT_PASSWORD` | DB credentials (match `DATABASE_URL`) |
| `BOOTSTRAP_ADMIN_PASSWORD` | Initial admin password (used once) |
| `DOMAIN` | `lab10.ifalabs.org` |
| `FLASK_APP` | leave as `run.py` |

`.env` is gitignored — never commit real secrets.

---

## 5. Deploy (HTTP)

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

The script builds the images, starts `app` (gunicorn) + `db` (MariaDB) +
`nginx` (HTTP reverse proxy on port 80), creates the schema (`flask init-db`)
and the admin user (`flask create-admin`).

Manual equivalent:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T app flask init-db
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T app flask create-admin
```

---

## 6. Open the firewall

On GCP the VM also needs a firewall rule allowing ingress on **tcp:80**
(and tcp:443 if you enable TLS). Either via the Cloud Console or:

```bash
gcloud compute firewall-rules create allow-http --allow tcp:80 --direction INGRESS
```

---

## 7. Verify

```bash
curl http://lab10.ifalabs.org/api/v1/health
# {"service":"flightdeck-dg-hub","status":"ok"}
```

Then open `http://lab10.ifalabs.org/` in a browser, register a user, and create
an API token under **/admin** to test the authenticated API:

```bash
API_TOKEN="<id>.<secret>" ./scripts/test_api_login.sh http://lab10.ifalabs.org
```

---

## 8. Optional: enable HTTPS (Let's Encrypt)

The repo also ships a TLS nginx template (`nginx/templates/flightdeck.conf.template`).
To switch to HTTPS:

1. Ensure `DOMAIN` resolves to the VM (it does: `lab10.ifalabs.org`).
2. Issue a certificate with certbot (webroot `./certbot/www`), e.g.:
   ```bash
   docker run --rm -v "$PWD/certbot/conf:/etc/letsencrypt" \
     -v "$PWD/certbot/www:/var/www/certbot" certbot/certbot \
     certonly --webroot -w /var/www/certbot -d lab10.ifalabs.org \
     --email <you@example.com> --agree-tos --no-eff-email
   ```
3. Use the base `docker-compose.yml` (TLS template) instead of the `-http`
   override, set `COOKIE_SECURE=1` in `.env`, and restart.

---

## 9. Operations

```bash
# logs
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f app

# stop / start
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# DB backup
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db \
  sh -c 'mariadb-dump -u root -p"$MARIADB_ROOT_PASSWORD" flightdeck' > backup.sql
```

Data persists in the `db_data` Docker volume, so app containers can be rebuilt
without data loss.
