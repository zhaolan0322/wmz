#!/usr/bin/env python3
import json
import re
import sys
import urllib.request
from pathlib import Path

PRIMARY = "https://github.com/openclaw/openclaw/releases"
BACKUP = "https://api.github.com/repos/openclaw/openclaw/releases"
RISK_WORDS = ["breaking", "migration", "deprecated", "remove", "rename"]

def fetch(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "openclaw-update-skill"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="ignore")

def parse_primary_latest_tag(html: str):
    m = re.search(r'/openclaw/openclaw/releases/tag/([^"\']+)', html)
    return m.group(1) if m else None

def risk_level(text: str):
    t = text.lower()
    hits = [w for w in RISK_WORDS if w in t]
    if any(w in t for w in ["breaking", "migration", "remove"]):
        lvl = "breaking"
    elif hits:
        lvl = "caution"
    else:
        lvl = "safe"
    return lvl, hits

def main():
    if len(sys.argv) < 2:
        print("usage: fetch_releases.py <run_dir>", file=sys.stderr)
        sys.exit(1)

    run_dir = Path(sys.argv[1])
    run_dir.mkdir(parents=True, exist_ok=True)

    out = {
        "primary_url": PRIMARY,
        "backup_url": BACKUP,
        "primary_latest_tag": None,
        "backup_latest_tag": None,
        "primary_backup_match": False,
        "risk_level": "caution",
        "risk_hits": [],
    }

    primary_html = ""
    backup_raw = ""
    try:
        primary_html = fetch(PRIMARY)
        out["primary_latest_tag"] = parse_primary_latest_tag(primary_html)
    except Exception as e:
        out["primary_error"] = str(e)

    try:
        backup_raw = fetch(BACKUP)
        releases = json.loads(backup_raw)
        if isinstance(releases, list) and releases:
            out["backup_latest_tag"] = releases[0].get("tag_name")
            out["backup_latest_name"] = releases[0].get("name")
            out["backup_latest_published_at"] = releases[0].get("published_at")
            body = releases[0].get("body") or ""
            lvl, hits = risk_level(body)
            out["risk_level"] = lvl
            out["risk_hits"] = hits
    except Exception as e:
        out["backup_error"] = str(e)

    out["primary_backup_match"] = bool(out["primary_latest_tag"] and out["backup_latest_tag"] and out["primary_latest_tag"] == out["backup_latest_tag"])

    p = run_dir / "release-info.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(p.read_text(encoding="utf-8"))

if __name__ == "__main__":
    main()
