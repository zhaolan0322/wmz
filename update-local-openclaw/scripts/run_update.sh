#!/usr/bin/env bash
set -euo pipefail

MODE=""
RUN_DIR=""
CHANNEL=""
TAG=""
NO_RESTART="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) MODE="$2"; shift 2 ;;
    --run-dir) RUN_DIR="$2"; shift 2 ;;
    --channel) CHANNEL="$2"; shift 2 ;;
    --tag) TAG="$2"; shift 2 ;;
    --no-restart) NO_RESTART="true"; shift ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$MODE" || -z "$RUN_DIR" ]]; then
  echo "usage: $0 --mode dry-run|apply --run-dir <dir> [--channel stable|beta|dev] [--tag vX] [--no-restart]" >&2
  exit 1
fi
mkdir -p "$RUN_DIR"

CMD=(openclaw update)
[[ -n "$CHANNEL" ]] && CMD+=(--channel "$CHANNEL")
[[ -n "$TAG" ]] && CMD+=(--tag "$TAG")

if [[ "$MODE" == "dry-run" ]]; then
  CMD+=(--dry-run)
  "${CMD[@]}" | tee "$RUN_DIR/dryrun.log"
  exit 0
fi

fallback_pkg_update() {
  local app_dir="/opt/openclaw-app"
  local spec="openclaw@latest"
  [[ -n "$TAG" ]] && spec="openclaw@$TAG"

  echo "[fallback] package-manager update start ($spec)" | tee -a "$RUN_DIR/update.log"

  if [[ -f "$app_dir/package.json" ]]; then
    if command -v pnpm >/dev/null 2>&1; then
      (cd "$app_dir" && pnpm add "$spec") | tee -a "$RUN_DIR/update.log"
      return 0
    fi
    if command -v npm >/dev/null 2>&1; then
      (cd "$app_dir" && npm install "$spec") | tee -a "$RUN_DIR/update.log"
      return 0
    fi
  fi

  if command -v npm >/dev/null 2>&1; then
    npm i -g "$spec" | tee -a "$RUN_DIR/update.log"
    return 0
  fi

  echo "[fallback] no package manager available" | tee -a "$RUN_DIR/update.log"
  return 1
}

if [[ "$MODE" == "apply" ]]; then
  if [[ "$NO_RESTART" == "true" ]]; then
    CMD+=(--no-restart)
  fi

  set +e
  "${CMD[@]}" | tee "$RUN_DIR/update.log"
  rc=${PIPESTATUS[0]}
  set -e

  if grep -Eq "Update Result: SKIPPED|not-git-install|package manager couldn't be detected" "$RUN_DIR/update.log"; then
    fallback_pkg_update
    openclaw doctor | tee -a "$RUN_DIR/update.log" || true
  elif [[ $rc -ne 0 ]]; then
    echo "openclaw update failed (rc=$rc)" | tee -a "$RUN_DIR/update.log"
    exit "$rc"
  fi

  exit 0
fi

echo "invalid mode: $MODE" >&2
exit 1
