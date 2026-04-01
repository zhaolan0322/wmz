#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="${1:-}"
if [[ -z "$RUN_DIR" ]]; then
  echo "usage: $0 <run_dir>" >&2
  exit 1
fi
mkdir -p "$RUN_DIR/snapshot"

TS="$(date +%Y%m%d-%H%M%S)"
SNAP_DIR="$RUN_DIR/snapshot/$TS"
mkdir -p "$SNAP_DIR"

copy_if_exists() {
  local src="$1"; local dst="$2"
  if [[ -e "$src" ]]; then
    cp -a "$src" "$dst"
  fi
}

copy_if_exists "$HOME/.openclaw/openclaw.json" "$SNAP_DIR/openclaw.json"
copy_if_exists "$HOME/.openclaw/credentials" "$SNAP_DIR/credentials"
copy_if_exists "$HOME/.openclaw/workspace" "$SNAP_DIR/workspace"

cat > "$RUN_DIR/rollback-manifest.json" <<EOF
{
  "snapshot_dir": "$SNAP_DIR",
  "created_at": "$(date -Iseconds)",
  "from_version": "$(openclaw --version 2>/dev/null || true)"
}
EOF

echo "$SNAP_DIR"
