#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$HOME/.openclaw/update-local-openclaw/runs"
TS="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$BASE_DIR/$TS"
CHANNEL=""
TAG=""
FORCE="false"
DO_RESTART="false"
OBSERVE_MINUTES="10"
COMMS_WAIT_SECONDS="600"
COMMS_RETRY_INTERVAL="15"
START_TS="$(date +%s)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run-dir) RUN_DIR="$2"; shift 2 ;;
    --channel) CHANNEL="$2"; shift 2 ;;
    --tag) TAG="$2"; shift 2 ;;
    --force) FORCE="true"; shift ;;
    --restart) DO_RESTART="true"; shift ;;
    --observe-minutes) OBSERVE_MINUTES="$2"; shift 2 ;;
    --comms-wait-seconds) COMMS_WAIT_SECONDS="$2"; shift 2 ;;
    --comms-retry-interval) COMMS_RETRY_INTERVAL="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

emit() {
  local stage="$1"
  local status="$2"
  local msg="$3"
  local now iso elapsed
  now="$(date +%s)"
  iso="$(date -Iseconds)"
  elapsed=$(( now - START_TS ))
  printf '[%s] [%s] %s (elapsed=%ss)\n' "$stage" "$status" "$msg" "$elapsed" | tee -a "$RUN_DIR/progress.log"
  printf '{"time":"%s","stage":"%s","status":"%s","message":%q,"elapsed_seconds":%s}\n' "$iso" "$stage" "$status" "$msg" "$elapsed" >> "$RUN_DIR/progress.jsonl"
}

wait_for_comms() {
  local phase="$1"
  local deadline=$(( $(date +%s) + COMMS_WAIT_SECONDS ))
  while true; do
    if "$SCRIPT_DIR/check_bot_comms.sh" "$RUN_DIR" "$phase" >/dev/null 2>&1; then
      "$SCRIPT_DIR/check_bot_comms.sh" "$RUN_DIR" "$phase" >/dev/null
      emit "comms-$phase" "ok" "all required bots online"
      return 0
    fi
    if [[ $(date +%s) -ge $deadline ]]; then
      emit "comms-$phase" "error" "comms check timeout after ${COMMS_WAIT_SECONDS}s"
      "$SCRIPT_DIR/check_bot_comms.sh" "$RUN_DIR" "$phase" >/dev/null || true
      return 2
    fi
    emit "comms-$phase" "waiting" "waiting for bots online; retry in ${COMMS_RETRY_INTERVAL}s"
    sleep "$COMMS_RETRY_INTERVAL"
  done
}

mkdir -p "$RUN_DIR"
: > "$RUN_DIR/progress.log"
: > "$RUN_DIR/progress.jsonl"

emit "baseline" "start" "collecting install baseline"
"$SCRIPT_DIR/check_install_method.sh" "$RUN_DIR" >/dev/null
"$SCRIPT_DIR/assert_baseline_safe.sh" "$RUN_DIR" >/dev/null
emit "baseline" "ok" "baseline collected"

emit "doctor-gate" "start" "checking hard blockers before update"
if ! "$SCRIPT_DIR/check_doctor_gate.sh" "$RUN_DIR" >/dev/null 2>&1; then
  emit "doctor-gate" "error" "doctor reported hard blockers; stop before update"
  "$SCRIPT_DIR/check_doctor_gate.sh" "$RUN_DIR" >/dev/null || true
  "$SCRIPT_DIR/run_summary.sh" "$RUN_DIR" >/dev/null || true
  exit 2
fi
emit "doctor-gate" "ok" "no hard blockers found"

emit "precheck" "start" "bot communication gate pre-update"
wait_for_comms pre
emit "web-pre" "start" "web gateway health pre-update"
"$SCRIPT_DIR/check_web_health.sh" "$RUN_DIR" pre >/dev/null
emit "web-pre" "ok" "web gateway reachable"

emit "releases" "start" "fetching release info"
python3 "$SCRIPT_DIR/fetch_releases.py" "$RUN_DIR" >/dev/null
emit "releases" "ok" "release info fetched"

MATCH="$(python3 - <<'PY' "$RUN_DIR/release-info.json"
import json,sys
x=json.load(open(sys.argv[1]))
print(str(x.get('primary_backup_match', False)).lower())
PY
)"
if [[ "$MATCH" != "true" && "$FORCE" != "true" ]]; then
  emit "releases" "error" "primary/backup release mismatch; stop (use --force to override)"
  exit 2
fi

emit "snapshot" "start" "creating rollback snapshot"
"$SCRIPT_DIR/snapshot.sh" "$RUN_DIR" >/dev/null
emit "snapshot" "ok" "snapshot created"

COMMON_ARGS=()
[[ -n "$CHANNEL" ]] && COMMON_ARGS+=(--channel "$CHANNEL")
[[ -n "$TAG" ]] && COMMON_ARGS+=(--tag "$TAG")

emit "dry-run" "start" "running openclaw update --dry-run"
"$SCRIPT_DIR/run_update.sh" --mode dry-run --run-dir "$RUN_DIR" "${COMMON_ARGS[@]}" >/dev/null
emit "dry-run" "ok" "dry-run passed"

emit "apply" "start" "running update apply with --no-restart"
"$SCRIPT_DIR/run_update.sh" --mode apply --run-dir "$RUN_DIR" --no-restart "${COMMON_ARGS[@]}" >/dev/null
emit "apply" "ok" "apply step completed"

emit "midcheck" "start" "bot communication gate mid-update"
wait_for_comms mid
emit "web-mid" "start" "web gateway health mid-update"
"$SCRIPT_DIR/check_web_health.sh" "$RUN_DIR" mid >/dev/null
emit "web-mid" "ok" "web gateway reachable after apply"

TARGET="$TAG"
if [[ -z "$TARGET" ]]; then
  TARGET="$(python3 - <<'PY' "$RUN_DIR/release-info.json"
import json,sys
x=json.load(open(sys.argv[1]))
print(x.get('backup_latest_tag') or x.get('primary_latest_tag') or '')
PY
)"
fi

emit "postcheck-pre" "start" "running pre-restart checks"
"$SCRIPT_DIR/postcheck.sh" "$RUN_DIR" "$TARGET" pending 1 >/dev/null || true
emit "postcheck-pre" "ok" "pre-restart checks complete"

if [[ "$DO_RESTART" == "true" ]]; then
  emit "restart" "start" "restarting gateway with fallback"
  "$SCRIPT_DIR/restart_with_fallback.sh" "$RUN_DIR" >/dev/null || true
  RSTATE="$(python3 - <<'PY' "$RUN_DIR/restart-state.json"
import json,sys
try:
  print(json.load(open(sys.argv[1])).get('restart_state','failed'))
except Exception:
  print('failed')
PY
)"
  if [[ "$RSTATE" == "done" ]]; then
    emit "restart" "ok" "gateway restart completed"
    "$SCRIPT_DIR/postcheck.sh" "$RUN_DIR" "$TARGET" done "$OBSERVE_MINUTES" >/dev/null
    wait_for_comms post
  elif [[ "$RSTATE" == "rolled_back" ]]; then
    emit "restart" "warn" "restart failed then rollback recovered"
    "$SCRIPT_DIR/postcheck.sh" "$RUN_DIR" "$TARGET" rolled_back 1 >/dev/null || true
    wait_for_comms post || true
  else
    emit "restart" "error" "restart failed"
    "$SCRIPT_DIR/postcheck.sh" "$RUN_DIR" "$TARGET" failed 1 >/dev/null || true
  fi
else
  emit "restart" "pending" "restart skipped by option"
fi

emit "summary" "start" "generating run summary"
"$SCRIPT_DIR/run_summary.sh" "$RUN_DIR" >/dev/null
emit "summary" "ok" "run summary generated"

echo "$RUN_DIR"
