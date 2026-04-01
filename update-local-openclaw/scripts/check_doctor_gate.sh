#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="${1:-}"
if [[ -z "$RUN_DIR" ]]; then
  echo "usage: $0 <run_dir>" >&2
  exit 1
fi
mkdir -p "$RUN_DIR"

OUT="$(openclaw doctor 2>&1 || true)"
LOWER="$(printf '%s' "$OUT" | tr '[:upper:]' '[:lower:]')"

BLOCKERS=()
check_blocker() {
  local needle="$1"
  if printf '%s' "$LOWER" | grep -Fqi "$needle"; then
    BLOCKERS+=("$needle")
  fi
}

check_blocker "token missing"
check_blocker "entrypoint missing"
check_blocker "service config mismatch"
check_blocker "multiple gateways"
check_blocker "state dir migration skipped"
check_blocker "target already exists"
check_blocker "config mismatch"

BLOCKED=false
[[ ${#BLOCKERS[@]} -gt 0 ]] && BLOCKED=true

python3 - <<'PY' "$RUN_DIR/doctor-gate.json" "$BLOCKED" "${BLOCKERS[*]}" "$OUT"
import json,sys
path,blocked,blockers,out=sys.argv[1:5]
with open(path,'w',encoding='utf-8') as f:
    json.dump({
        'blocked': blocked.lower()=='true',
        'blockers': [x for x in blockers.split(' ') if x],
        'checked_at': __import__('datetime').datetime.now().astimezone().isoformat(),
        'doctor_excerpt': out[:6000]
    }, f, ensure_ascii=False, indent=2)
print(path)
PY

cat "$RUN_DIR/doctor-gate.json"
[[ "$BLOCKED" != "true" ]]
