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

## 8. Trusted HTTPS with Let's Encrypt (certbot)

This is the procedure actually used to put a browser-trusted certificate on
`lab10.ifalabs.org`. It uses certbot's **standalone** HTTP-01 challenge: nginx is
stopped briefly so certbot can bind port 80 itself, then restarted with the new
certificate. The stack runs with the TLS override
(`docker-compose.yml` + `docker-compose.tls.yml`), where nginx serves
`./certs/fullchain.pem` and `./certs/privkey.pem`.

### 8.1 Prerequisites (verify before issuing)

| Requirement | Why | Check |
| --- | --- | --- |
| Public **A-record** `DOMAIN → VM public IP` | HTTP-01 must reach this host | `nslookup lab10.ifalabs.org` → `34.65.14.54` |
| **tcp:80** open to the internet | ACME challenge | `curl -I http://lab10.ifalabs.org/` from outside |
| **tcp:443** open | serve HTTPS | already used by the running stack |
| `DOMAIN` / `LETSENCRYPT_EMAIL` set in `.env` | cert subject + expiry notices | `grep -E 'DOMAIN|LETSENCRYPT_EMAIL' .env` |

> **Rate limits:** Let's Encrypt allows ~5 failed validations/hour and 50 certs/week
> per domain. **Always run the staging dry-run first** (step 8.2) — it does not count
> against the production limits.

### 8.2 Issue the certificate

Run from the repo root on the VM (`~/flightdeck`). Set `DOMAIN`/`EMAIL` to match `.env`.

```bash
DOMAIN=lab10.ifalabs.org
EMAIL=admin@ifalabs.org
DC="sudo docker compose -f docker-compose.yml -f docker-compose.tls.yml"
mkdir -p certbot/conf certbot/www certs

# 1) Free port 80 (brief downtime starts here)
$DC stop nginx

# 2) Staging dry-run — proves DNS + port 80 work, no rate-limit cost
sudo docker run --rm -p 80:80 \
  -v "$PWD/certbot/conf:/etc/letsencrypt" -v "$PWD/certbot/www:/var/www/certbot" \
  certbot/certbot certonly --standalone --dry-run \
  -d "$DOMAIN" --email "$EMAIL" --agree-tos --no-eff-email -n

# 3) Only if the dry-run succeeded: request the REAL certificate
sudo docker run --rm -p 80:80 \
  -v "$PWD/certbot/conf:/etc/letsencrypt" -v "$PWD/certbot/www:/var/www/certbot" \
  certbot/certbot certonly --standalone \
  -d "$DOMAIN" --email "$EMAIL" --agree-tos --no-eff-email -n

# 4) Install the cert where nginx expects it
sudo cp -L "certbot/conf/live/$DOMAIN/fullchain.pem" certs/fullchain.pem
sudo cp -L "certbot/conf/live/$DOMAIN/privkey.pem"  certs/privkey.pem

# 5) Bring nginx back (downtime ends)
$DC up -d nginx
```

Make sure `COOKIE_SECURE=1` is set in `.env` (it is, when the stack was first
provisioned in a TLS mode) so session cookies get the `Secure` flag.

### 8.3 Verify

```bash
# From outside the VM — note: NO -k, so the cert chain is actually validated
curl -s -w '\nHTTP %{http_code}\n' https://lab10.ifalabs.org/api/v1/health
# → {"service":"flightdeck-dg-hub","status":"ok"}  HTTP 200

# Inspect issuer / validity on the VM
sudo openssl x509 -in certs/fullchain.pem -noout -issuer -subject -enddate
# issuer=... O = Let's Encrypt ...   notAfter=<~90 days out>
```

A trusted cert means the browser opens `https://lab10.ifalabs.org/` with no warning.

### 8.4 Renewal (important — certs last 90 days)

The certificate above expires after **90 days**. A single cert covers a short
correction window, but for anything longer set up automatic renewal. The standalone
method needs port 80, so a renewal either briefly stops nginx or uses the webroot
that nginx already mounts (`./certbot/www` → `/var/www/certbot`).

The TLS nginx config already serves `/.well-known/acme-challenge/` from
`/var/www/certbot`, so renewal uses the **webroot** challenge with nginx running
(no downtime). The repo ships `scripts/renew-cert.sh`, which renews, installs the
cert into `./certs`, and reloads nginx.

Test it first (staging, no rate-limit cost):

```bash
sudo bash scripts/renew-cert.sh --dry-run
```

Then install a weekly root cron job:

```bash
# as root (sudo crontab -e), one line:
0 3 * * 1 /bin/bash /home/student/flightdeck/scripts/renew-cert.sh >> /var/log/flightdeck-renew.log 2>&1
```

`certbot renew` is a no-op until the cert is within ~30 days of expiry, so running
weekly is safe.

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
