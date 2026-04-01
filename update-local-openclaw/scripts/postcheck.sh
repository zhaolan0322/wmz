#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="${1:-}"
TARGET_VERSION="${2:-}"
RESTART_STATE="${3:-pending}"
OBSERVE_MINUTES="${4:-10}"

if [[ -z "$RUN_DIR" ]]; then
  echo "usage: $0 <run_dir> [target_version] [restart_state] [observe_minutes]" >&2
  exit 1
fi
mkdir -p "$RUN_DIR"

VER="$(openclaw --version 2>/dev/null || true)"
set +e
STATUS_OUT="$(openclaw status 2>&1)"; STATUS_RC=$?
HEALTH_OUT="$(openclaw health 2>&1)"; HEALTH_RC=$?
openclaw --version >/dev/null 2>&1; VER_RC=$?
openclaw status >/dev/null 2>&1; STATUS_SMOKE_RC=$?
"$(dirname "$0")/check_web_health.sh" "$RUN_DIR" postcheck >/dev/null 2>&1; WEB_RC=$?
set -e

G1_VERSION_MATCH="false"
NORMALIZED_TARGET="${TARGET_VERSION#v}"
if [[ -n "$TARGET_VERSION" ]]; then
  if [[ "$VER" == *"$TARGET_VERSION"* || "$VER" == *"$NORMALIZED_TARGET"* ]]; then
    G1_VERSION_MATCH="true"
  fi
else
  [[ -n "$VER" ]] && G1_VERSION_MATCH="true"
fi

G2_STATUS_OK="false"
[[ $STATUS_RC -eq 0 ]] && G2_STATUS_OK="true"

G3_HEALTH_OK="false"
if [[ $HEALTH_RC -eq 0 ]] || echo "$HEALTH_OUT" | grep -Eqi "healthy|ok|pass"; then
  G3_HEALTH_OK="true"
fi

G4_SMOKE_OK="false"
if [[ $VER_RC -eq 0 && $STATUS_SMOKE_RC -eq 0 ]]; then
  G4_SMOKE_OK="true"
fi

G5_OBSERVE_OK="false"
if [[ "$RESTART_STATE" == "done" || "$RESTART_STATE" == "rolled_back" ]]; then
  STEP=$(( OBSERVE_MINUTES < 1 ? 60 : OBSERVE_MINUTES*60/2 ))
  [[ $STEP -lt 30 ]] && STEP=30
  set +e
  openclaw status >/dev/null 2>&1 && sleep "$STEP" && openclaw status >/dev/null 2>&1
  OBS_RC=$?
  set -e
  [[ $OBS_RC -eq 0 ]] && G5_OBSERVE_OK="true"
fi

G6_WEB_OK="false"
[[ $WEB_RC -eq 0 ]] && G6_WEB_OK="true"

FINAL_STATUS="PARTIAL"
if [[ "$G1_VERSION_MATCH" == "true" && "$G2_STATUS_OK" == "true" && "$G3_HEALTH_OK" == "true" && "$G4_SMOKE_OK" == "true" && "$G5_OBSERVE_OK" == "true" && "$G6_WEB_OK" == "true" ]]; then
  FINAL_STATUS="SUCCESS"
fi

cat > "$RUN_DIR/postcheck.json" <<EOF
{
  "version": "${VER}",
  "target_version": "${TARGET_VERSION}",
  "restart_state": "${RESTART_STATE}",
  "gates": {
    "g1_version_match": ${G1_VERSION_MATCH},
    "g2_status_ok": ${G2_STATUS_OK},
    "g3_health_ok": ${G3_HEALTH_OK},
    "g4_smoke_ok": ${G4_SMOKE_OK},
    "g5_observe_ok": ${G5_OBSERVE_OK},
    "g6_web_ok": ${G6_WEB_OK}
  },
  "result": "${FINAL_STATUS}",
  "checked_at": "$(date -Iseconds)"
}
EOF

cat "$RUN_DIR/postcheck.json"
