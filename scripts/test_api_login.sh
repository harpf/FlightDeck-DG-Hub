#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:5000}"
LOGIN_PATH="${LOGIN_PATH:-/auth/login}"
MEMBERS_PATH="${MEMBERS_PATH:-/api/members}"
EVENTS_PATH="${EVENTS_PATH:-/api/events}"
USERNAME="${USERNAME:-admin}"
PASSWORD="${PASSWORD:-admin1234}"

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

COOKIE_JAR="$WORKDIR/cookies.txt"
LOGIN_HTML="$WORKDIR/login.html"
LOGIN_RESPONSE="$WORKDIR/after_login.html"

echo "Using BASE_URL=$BASE_URL"

echo
echo "1) Fetching login page and CSRF token ..."
curl -sS -c "$COOKIE_JAR" -b "$COOKIE_JAR" "${BASE_URL}${LOGIN_PATH}" > "$LOGIN_HTML"

CSRF_TOKEN="$(grep -oP 'name="csrf_token"[^>]*value="\K[^"]+' "$LOGIN_HTML" || true)"

if [[ -z "$CSRF_TOKEN" ]]; then
  echo "ERROR: Could not extract csrf_token from login page."
  echo "Saved login page to: $LOGIN_HTML"
  exit 1
fi

echo "CSRF token found."

echo
echo "2) Logging in as $USERNAME ..."
curl -sS -L \
  -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
  -X POST "${BASE_URL}${LOGIN_PATH}" \
  --data-urlencode "csrf_token=$CSRF_TOKEN" \
  --data-urlencode "username=$USERNAME" \
  --data-urlencode "password=$PASSWORD" \
  --data-urlencode "submit=Anmelden" \
  > "$LOGIN_RESPONSE"

echo "Login request completed."

echo
echo "3) Checking /api/members ..."
MEMBERS_STATUS="$(curl -sS -o "$WORKDIR/members.json" -w "%{http_code}" -b "$COOKIE_JAR" "${BASE_URL}${MEMBERS_PATH}")"
echo "HTTP status: $MEMBERS_STATUS"
if [[ "$MEMBERS_STATUS" == "200" ]]; then
  echo "--- /api/members response ---"
  cat "$WORKDIR/members.json"
  echo
else
  echo "ERROR: /api/members returned HTTP $MEMBERS_STATUS"
  echo "Response:"
  cat "$WORKDIR/members.json"
  echo
fi

echo
echo "4) Checking /api/events ..."
EVENTS_STATUS="$(curl -sS -o "$WORKDIR/events.json" -w "%{http_code}" -b "$COOKIE_JAR" "${BASE_URL}${EVENTS_PATH}")"
echo "HTTP status: $EVENTS_STATUS"
if [[ "$EVENTS_STATUS" == "200" ]]; then
  echo "--- /api/events response ---"
  cat "$WORKDIR/events.json"
  echo
else
  echo "ERROR: /api/events returned HTTP $EVENTS_STATUS"
  echo "Response:"
  cat "$WORKDIR/events.json"
  echo
fi

echo
if [[ "$MEMBERS_STATUS" == "200" && "$EVENTS_STATUS" == "200" ]]; then
  echo "API test successful."
  exit 0
else
  echo "API test finished with errors."
  exit 2
fi
