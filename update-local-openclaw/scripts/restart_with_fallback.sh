#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="${1:-}"
if [[ -z "$RUN_DIR" ]]; then
  echo "usage: $0 <run_dir>" >&2
  exit 1
fi
mkdir -p "$RUN_DIR"

STATE="failed"
DETAIL="restart failed"

try_cmd() {
  set +e
  "$@" >/dev/null 2>&1
  local rc=$?
  set -e
  return $rc
}

health_ok() {
  set +e
  local out rc
  out="$(openclaw health 2>&1)"
  rc=$?
  set -e
  [[ $rc -eq 0 ]] || return 1
  printf '%s' "$out" | grep -Eqi 'Telegram:\s*ok|Telegram .* OK' || return 1
  "$SCRIPT_DIR/check_web_health.sh" "$RUN_DIR" restart >/dev/null 2>&1 || return 1
  return 0
}

force_start_gateway() {
  try_cmd openclaw gateway stop
  nohup openclaw gateway --port 18790 --force >"$RUN_DIR/force-start.log" 2>&1 &
  echo $! > "$RUN_DIR/force-start.pid"
  sleep 4
  health_ok
}

if try_cmd openclaw gateway restart && health_ok; then
  STATE="done"
  DETAIL="restart ok"
else
  if try_cmd openclaw gateway stop && try_cmd openclaw gateway start && health_ok; then
    STATE="done"
    DETAIL="stop/start fallback ok"
  else
    try_cmd openclaw doctor --fix
    if (try_cmd openclaw gateway restart || (try_cmd openclaw gateway stop && try_cmd openclaw gateway start)) && health_ok; then
      STATE="done"
      DETAIL="doctor --fix + restart fallback ok"
    else
      if "$SCRIPT_DIR/rollback.sh" "$RUN_DIR" >/dev/null 2>&1; then
        if (try_cmd openclaw gateway restart || (try_cmd openclaw gateway stop && try_cmd openclaw gateway start)) && health_ok; then
          STATE="rolled_back"
          DETAIL="rollback succeeded and service recovered"
        elif force_start_gateway; then
          STATE="rolled_back"
          DETAIL="rollback + force-start recovered"
        else
          STATE="failed"
          DETAIL="rollback executed but service still failed"
        fi
      else
        if force_start_gateway; then
          STATE="done"
          DETAIL="force-start recovered without rollback"
        else
          STATE="failed"
          DETAIL="restart fallback + doctor + rollback + force-start all failed"
        fi
      fi
    fi
  fi
fi

cat > "$RUN_DIR/restart-state.json" <<EOF
{
  "restart_state": "${STATE}",
  "detail": "${DETAIL}",
  "checked_at": "$(date -Iseconds)"
}
EOF

cat "$RUN_DIR/restart-state.json"
