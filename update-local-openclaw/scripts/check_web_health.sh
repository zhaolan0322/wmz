#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="${1:-}"
PHASE="${2:-pre}"
TIMEOUT="${3:-5}"
if [[ -z "$RUN_DIR" ]]; then
  echo "usage: $0 <run_dir> [phase] [timeout_seconds]" >&2
  exit 1
fi
mkdir -p "$RUN_DIR"

get_gateway_url() {
  set +e
  local line url
  line="$(openclaw status 2>/dev/null | grep -E 'Dashboard|Gateway' | head -n 1)"
  set -e
  url="$(printf '%s' "$line" | grep -Eo 'https?://[^ ]+' | head -n 1 || true)"
  if [[ -z "$url" ]]; then
    url="http://127.0.0.1:18790/"
  fi
  printf '%s' "$url"
}

URL="$(get_gateway_url)"
set +e
HEADERS="$(curl -k -I -L --max-time "$TIMEOUT" "$URL" 2>&1)"
CURL_RC=$?
BODY="$(curl -k -L --max-time "$TIMEOUT" "$URL" 2>&1 | head -c 4000)"
set -e

HTTP_CODE="$(printf '%s' "$HEADERS" | awk '/^HTTP\//{code=$2} END{print code}')"
WEB_OK=false
if [[ $CURL_RC -eq 0 ]] && [[ "$HTTP_CODE" =~ ^(200|301|302|401|403)$ ]]; then
  WEB_OK=true
fi

cat > "$RUN_DIR/web-${PHASE}.json" <<EOF
{
  "phase": "${PHASE}",
  "url": "${URL}",
  "curl_rc": ${CURL_RC},
  "http_code": "${HTTP_CODE}",
  "web_ok": ${WEB_OK},
  "checked_at": "$(date -Iseconds)"
}
EOF

cat "$RUN_DIR/web-${PHASE}.json"

if [[ "$WEB_OK" != "true" ]]; then
  printf '\n--- response preview ---\n%s\n' "$BODY" >&2
  exit 2
fi
