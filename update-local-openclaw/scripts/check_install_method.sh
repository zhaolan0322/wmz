#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="${1:-}"
if [[ -z "$RUN_DIR" ]]; then
  echo "usage: $0 <run_dir>" >&2
  exit 1
fi
mkdir -p "$RUN_DIR"

OPENCLAW_BIN="$(command -v openclaw || true)"
OPENCLAW_VER="$(openclaw --version 2>/dev/null || true)"
APP_DIR="/opt/openclaw-app"
METHODS=()

if [[ -f "$APP_DIR/package.json" ]] && grep -q '"openclaw"' "$APP_DIR/package.json" 2>/dev/null; then
  METHODS+=("app-dir-package")
fi
if npm list -g openclaw --depth=0 >/dev/null 2>&1; then
  METHODS+=("npm-global")
fi
if command -v pnpm >/dev/null 2>&1 && [[ -f "$APP_DIR/package.json" ]]; then
  if pnpm --dir "$APP_DIR" list openclaw --depth 0 >/dev/null 2>&1; then
    METHODS+=("pnpm-app-dir")
  fi
fi

if [[ ${#METHODS[@]} -eq 0 ]]; then
  METHOD="unknown"
elif [[ ${#METHODS[@]} -eq 1 ]]; then
  METHOD="${METHODS[0]}"
else
  METHOD="$(IFS=+; echo "${METHODS[*]}")"
fi

SYSTEMD_UNIT="$(systemctl --user list-unit-files 2>/dev/null | grep -E '^openclaw-gateway.service' | awk '{print $1}' | head -n1 || true)"
LISTENERS="$(ss -ltnp 2>/dev/null | grep ':18790' | head -n 5 | tr '\n' ';' || true)"
METHODS_JOINED="$(IFS='|'; echo "${METHODS[*]}")"

python3 - <<'PY' "$RUN_DIR/baseline.json" "$OPENCLAW_BIN" "$OPENCLAW_VER" "$METHOD" "$APP_DIR" "$SYSTEMD_UNIT" "$LISTENERS" "$METHODS_JOINED"
import json,sys
path,binp,ver,method,app_dir,systemd_unit,listeners,methods_joined=sys.argv[1:9]
methods=[x for x in methods_joined.split('|') if x]
obj={
    'openclaw_bin': binp,
    'openclaw_version': ver,
    'install_method': method,
    'install_methods_detected': methods,
    'app_dir': app_dir,
    'systemd_unit': systemd_unit,
    'listeners_18790': listeners,
}
with open(path,'w',encoding='utf-8') as f:
    json.dump(obj,f,ensure_ascii=False,indent=2)
print(json.dumps(obj,ensure_ascii=False,indent=2))
PY
