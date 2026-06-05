#!/usr/bin/env bash
#
# Headless smoke test for the FlightDeck DG Hub RESTful Web-API.
#
# The API is authenticated with a static API token (created by an admin in the
# web UI under /admin). The client sends it in the `X-API-Token` header — no
# browser and no session cookie required, which satisfies the assignment's
# "authentication without a browser" requirement.
#
# Usage:
#   API_TOKEN="<id>.<secret>" ./scripts/test_api_login.sh [BASE_URL]
#
# Example:
#   API_TOKEN="3.kJ8..." ./scripts/test_api_login.sh https://lab10.ifalabs.org
#
set -euo pipefail

BASE_URL="${1:-http://localhost:5000}"
API_TOKEN="${API_TOKEN:-}"

echo "Using BASE_URL=$BASE_URL"

echo
echo "1) Health endpoint (public, no token) ..."
curl -fsS "${BASE_URL}/api/v1/health"
echo

echo
echo "2) Products WITHOUT token (expect HTTP 401) ..."
STATUS="$(curl -sS -o /dev/null -w '%{http_code}' "${BASE_URL}/api/v1/products")"
echo "HTTP status: $STATUS"
if [[ "$STATUS" != "401" ]]; then
  echo "ERROR: expected 401 for unauthenticated request, got $STATUS"
  exit 1
fi

if [[ -z "$API_TOKEN" ]]; then
  echo
  echo "No API_TOKEN provided — skipping authenticated checks."
  echo "Create a token in the web UI (/admin) and re-run with API_TOKEN=... set."
  exit 0
fi

echo
echo "3) Products WITH token (expect HTTP 200) ..."
curl -fsS -H "X-API-Token: ${API_TOKEN}" "${BASE_URL}/api/v1/products"
echo

echo
echo "4) Full export WITH token ..."
curl -fsS -H "X-API-Token: ${API_TOKEN}" "${BASE_URL}/api/v1/full"
echo

echo
echo "API test successful."
