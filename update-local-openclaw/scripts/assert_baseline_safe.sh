#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="${1:-}"
if [[ -z "$RUN_DIR" ]]; then
  echo "usage: $0 <run_dir>" >&2
  exit 1
fi

python3 - <<'PY' "$RUN_DIR/baseline.json"
import json,sys
p=sys.argv[1]
obj=json.load(open(p))
method=obj.get('install_method','unknown')
issues=[]
if method == 'unknown':
    issues.append('install_method_unknown')
if '+' in method:
    issues.append('multiple_install_methods_detected')
if not obj.get('openclaw_bin'):
    issues.append('openclaw_bin_missing')
print(json.dumps({'pass': not issues, 'issues': issues}, ensure_ascii=False))
if issues:
    raise SystemExit(2)
PY
