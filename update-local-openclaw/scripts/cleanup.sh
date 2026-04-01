#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-}"
BASE_DIR="${2:-$HOME/.openclaw/update-local-openclaw/runs}"
RETENTION_HOURS="${RETENTION_HOURS:-72}"

if [[ -z "$MODE" ]]; then
  echo "usage: $0 now|final [runs_dir]" >&2
  exit 1
fi
mkdir -p "$BASE_DIR"
REPORT="$BASE_DIR/cleanup-report.json"

if [[ "$MODE" == "now" ]]; then
  find "$BASE_DIR" -type f \( -name "*.tmp" -o -name "dryrun.log" \) -mtime +1 -delete || true
  cat > "$REPORT" <<EOF
{"mode":"now","status":"done","at":"$(date -Iseconds)"}
EOF
  cat "$REPORT"
  exit 0
fi

if [[ "$MODE" == "final" ]]; then
  find "$BASE_DIR" -mindepth 1 -maxdepth 1 -type d -mmin +$((RETENTION_HOURS*60)) -exec rm -rf {} +
  cat > "$REPORT" <<EOF
{"mode":"final","retention_hours":${RETENTION_HOURS},"status":"done","at":"$(date -Iseconds)"}
EOF
  cat "$REPORT"
  exit 0
fi

echo "invalid mode: $MODE" >&2
exit 1
