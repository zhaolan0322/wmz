#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$HOME/.openclaw/update-local-openclaw/runs"
RUN_DIR="$BASE_DIR/$(date +%Y%m%d-%H%M%S)-bg"
mkdir -p "$RUN_DIR"

nohup "$SCRIPT_DIR/full_auto.sh" --run-dir "$RUN_DIR" "$@" > "$RUN_DIR/background.out.log" 2>&1 &
PID=$!
echo "$PID" > "$RUN_DIR/background.pid"

echo "RUN_DIR=$RUN_DIR"
echo "PID=$PID"
echo "LOG=$RUN_DIR/background.out.log"
