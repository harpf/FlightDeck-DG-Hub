#!/usr/bin/env bash
#
# One-shot deployment for FlightDeck DG Hub on the target host (HTTP-only).
# Run this FROM the server, inside the repository directory.
#
#   chmod +x scripts/deploy.sh
#   ./scripts/deploy.sh
#
# Prerequisites: Docker Engine + the docker compose plugin, and a .env file
# (copy from .env.example and fill in real secrets). See docs/DEPLOYMENT.md.
#
set -euo pipefail

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

if [[ ! -f .env ]]; then
  echo "ERROR: .env not found. Copy .env.example to .env and set real secrets first."
  exit 1
fi

echo ">> Building and starting containers ..."
$COMPOSE up -d --build

echo ">> Waiting for the database to accept connections ..."
for i in $(seq 1 30); do
  if $COMPOSE exec -T db sh -c 'mariadb-admin ping -h localhost -p"$MARIADB_ROOT_PASSWORD" --silent' >/dev/null 2>&1; then
    echo "   database is up."
    break
  fi
  sleep 2
done

echo ">> Creating database schema ..."
$COMPOSE exec -T app flask init-db

echo ">> Creating admin user (if BOOTSTRAP_ADMIN_PASSWORD is set) ..."
$COMPOSE exec -T app flask create-admin || true

echo ">> Running containers:"
$COMPOSE ps

echo
echo "Done. The site should be reachable on http://<host>/  and the API on http://<host>/api/v1/health"
