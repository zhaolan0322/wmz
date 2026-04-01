#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="${1:-}"
if [[ -z "$RUN_DIR" ]]; then
  echo "usage: $0 <run_dir>" >&2
  exit 1
fi

BASELINE="$RUN_DIR/baseline.json"
RELEASE="$RUN_DIR/release-info.json"
POST="$RUN_DIR/postcheck.json"
RESTART="$RUN_DIR/restart-state.json"
OUT="$RUN_DIR/run-summary.md"
COMMS_PRE="$RUN_DIR/comms-pre.json"
COMMS_MID="$RUN_DIR/comms-mid.json"
COMMS_POST="$RUN_DIR/comms-post.json"
WEB_PRE="$RUN_DIR/web-pre.json"
WEB_POST="$RUN_DIR/web-postcheck.json"
DOCTOR_GATE="$RUN_DIR/doctor-gate.json"

py_get() {
  python3 - "$1" "$2" <<'PY'
import json,sys
p,k=sys.argv[1],sys.argv[2]
try:
  d=json.load(open(p))
  cur=d
  for part in k.split('.'):
    cur=cur[part]
  print(cur)
except Exception:
  print("")
PY
}

FROM_VER="$(py_get "$BASELINE" openclaw_version)"
TO_VER="$(py_get "$POST" version)"
RISK="$(py_get "$RELEASE" risk_level)"
RESULT="$(py_get "$POST" result)"
RESTART_STATE="$(py_get "$RESTART" restart_state)"
[[ -z "$RESTART_STATE" ]] && RESTART_STATE="pending"
if [[ "$(py_get "$DOCTOR_GATE" blocked)" == "True" || "$(py_get "$DOCTOR_GATE" blocked)" == "true" ]]; then
  RESULT="BLOCKED"
fi
if [[ "$RESTART_STATE" == "rolled_back" ]]; then
  RESULT="ROLLED_BACK"
fi
COMM_PRE="$(py_get "$COMMS_PRE" pass)"; [[ -z "$COMM_PRE" ]] && COMM_PRE="n/a"
COMM_MID="$(py_get "$COMMS_MID" pass)"; [[ -z "$COMM_MID" ]] && COMM_MID="n/a"
COMM_POST="$(py_get "$COMMS_POST" pass)"; [[ -z "$COMM_POST" ]] && COMM_POST="n/a"
WEB_PRE_OK="$(py_get "$WEB_PRE" web_ok)"; [[ -z "$WEB_PRE_OK" ]] && WEB_PRE_OK="n/a"
WEB_POST_OK="$(py_get "$WEB_POST" web_ok)"; [[ -z "$WEB_POST_OK" ]] && WEB_POST_OK="n/a"
BLOCKERS="$(py_get "$DOCTOR_GATE" blockers)"

cat > "$OUT" <<EOF
# update-local-openclaw run summary

- Status: ${RESULT:-PARTIAL}
- From -> To: ${FROM_VER:-unknown} -> ${TO_VER:-unknown}
- Risk level: ${RISK:-caution}
- Restart state: ${RESTART_STATE}
- Run dir: ${RUN_DIR}
- Doctor gate blockers: ${BLOCKERS:-none}

## Gates
- g1 version match: $(py_get "$POST" gates.g1_version_match)
- g2 status ok: $(py_get "$POST" gates.g2_status_ok)
- g3 health ok: $(py_get "$POST" gates.g3_health_ok)
- g4 smoke ok: $(py_get "$POST" gates.g4_smoke_ok)
- g5 observe ok: $(py_get "$POST" gates.g5_observe_ok)
- g6 web ok: $(py_get "$POST" gates.g6_web_ok)

## Bot communication checks
- pre-update: ${COMM_PRE}
- mid-update (--no-restart): ${COMM_MID}
- post-restart: ${COMM_POST}

## Web checks
- pre-update: ${WEB_PRE_OK}
- postcheck: ${WEB_POST_OK}
EOF

echo "$OUT"
