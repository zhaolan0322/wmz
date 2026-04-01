#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="${1:-}"
PHASE="${2:-pre}"
if [[ -z "$RUN_DIR" ]]; then
  echo "usage: $0 <run_dir> [pre|mid|post]" >&2
  exit 1
fi
mkdir -p "$RUN_DIR"

OUT="$(openclaw health 2>&1 || true)"
TS="$(date -Iseconds)"

TELEGRAM_OK="false"
if printf '%s' "$OUT" | grep -Eqi 'Telegram:\s*ok|Telegram .* OK'; then
  TELEGRAM_OK="true"
fi

HAS_BAOZI="false"
HAS_FUGUI="false"
HAS_RESCUE="false"

printf '%s' "$OUT" | grep -qi 'baozi' && HAS_BAOZI="true"
printf '%s' "$OUT" | grep -qi 'fugui' && HAS_FUGUI="true"
printf '%s' "$OUT" | grep -Eqi 'main_rescue_bot|@main_rescue_bot|:rescue|\brescue\b' && HAS_RESCUE="true"

PASS="false"
if [[ "$TELEGRAM_OK" == "true" && "$HAS_BAOZI" == "true" && "$HAS_FUGUI" == "true" && "$HAS_RESCUE" == "true" ]]; then
  PASS="true"
fi

cat > "$RUN_DIR/comms-${PHASE}.json" <<EOF
{
  "phase": "${PHASE}",
  "telegram_ok": ${TELEGRAM_OK},
  "baozi_present": ${HAS_BAOZI},
  "fugui_present": ${HAS_FUGUI},
  "rescue_present": ${HAS_RESCUE},
  "pass": ${PASS},
  "checked_at": "${TS}"
}
EOF

cat "$RUN_DIR/comms-${PHASE}.json"

if [[ "$PASS" != "true" ]]; then
  exit 2
fi
