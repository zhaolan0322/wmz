from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from memory_system_runtime.core.config import ConfigBundle
from memory_system_runtime.protected.integrity_checker import IntegrityChecker
from memory_system_runtime.storage.protected_store import ProtectedStore


def main() -> None:
    config = ConfigBundle(ROOT)
    protected_root = Path(config.memory["paths"]["protected_root"])
    store = ProtectedStore(protected_root, config.memory["protected"]["manifest_file"])
    manifest = store.read_manifest()
    checker = IntegrityChecker()
    result = checker.check_manifest(protected_root, manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
