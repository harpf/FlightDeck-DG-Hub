#!/usr/bin/env bash
#
# Renew the Let's Encrypt certificate via the webroot challenge (no downtime),
# install it where nginx reads it, and reload nginx. Safe to run on a schedule:
# certbot only renews when the cert is within ~30 days of expiry, otherwise this
# is a no-op (the copy + reload are cheap and idempotent).
#
# Intended for cron (as root):
#   0 3 * * 1  /home/student/flightdeck/scripts/renew-cert.sh >> /var/log/flightdeck-renew.log 2>&1
#
# The TLS nginx config already serves /.well-known/acme-challenge/ from
# /var/www/certbot (mounted from ./certbot/www), so nginx stays up during renewal.
set -euo pipefail

cd "$(dirname "$0")/.."           # repository root (script lives in scripts/)
DOMAIN="${DOMAIN:-lab10.ifalabs.org}"
DC="docker compose -f docker-compose.yml -f docker-compose.tls.yml"

# Pass --dry-run through when testing:  ./scripts/renew-cert.sh --dry-run
EXTRA_ARGS="$*"

docker run --rm \
  -v "$PWD/certbot/conf:/etc/letsencrypt" \
  -v "$PWD/certbot/www:/var/www/certbot" \
  certbot/certbot renew --webroot -w /var/www/certbot -q $EXTRA_ARGS

# Skip install/reload on a dry-run (no real cert is written).
case "$EXTRA_ARGS" in
  *--dry-run*) echo "dry-run OK — webroot challenge works, nginx stayed up."; exit 0 ;;
esac

cp -L "certbot/conf/live/$DOMAIN/fullchain.pem" certs/fullchain.pem
cp -L "certbot/conf/live/$DOMAIN/privkey.pem"  certs/privkey.pem
$DC exec -T nginx nginx -s reload
echo "renew-cert: certificate checked/renewed and nginx reloaded."
