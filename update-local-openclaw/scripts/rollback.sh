#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="${1:-}"
if [[ -z "$RUN_DIR" ]]; then
  echo "usage: $0 <run_dir>" >&2
  exit 1
fi
MANIFEST="$RUN_DIR/rollback-manifest.json"

if [[ ! -f "$MANIFEST" ]]; then
  echo "rollback manifest not found: $MANIFEST" >&2
  exit 1
fi

SNAPSHOT_DIR="$(python3 - <<'PY' "$MANIFEST"
import json,sys
print(json.load(open(sys.argv[1]))['snapshot_dir'])
PY
)"

if [[ ! -d "$SNAPSHOT_DIR" ]]; then
  echo "snapshot dir missing: $SNAPSHOT_DIR" >&2
  exit 1
fi

[[ -f "$SNAPSHOT_DIR/openclaw.json" ]] && cp -a "$SNAPSHOT_DIR/openclaw.json" "$HOME/.openclaw/openclaw.json"
[[ -d "$SNAPSHOT_DIR/credentials" ]] && { rm -rf "$HOME/.openclaw/credentials"; cp -a "$SNAPSHOT_DIR/credentials" "$HOME/.openclaw/credentials"; }

echo "rollback config restore complete"
