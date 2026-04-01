from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


class IntegrityChecker:
    def check_manifest(self, protected_root: Path, manifest: dict) -> dict:
        files = manifest.get("files", [])
        if not files:
            return {"status": "missing_manifest_entries", "details": []}
        details = []
        overall = "pass"
        for entry in files:
            path = Path(entry["path"])
            if not path.is_absolute():
                path = protected_root.parent.parent / path
            if not path.exists():
                overall = "missing_file"
                details.append({"path": str(path), "status": "missing_file"})
                continue
            actual = sha256_file(path)
            if actual != entry["sha256"]:
                overall = "hash_mismatch"
                details.append({"path": str(path), "status": "hash_mismatch"})
            else:
                details.append({"path": str(path), "status": "pass"})
        return {"status": overall, "details": details}
