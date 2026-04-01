from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class ConfigBundle:
    def __init__(self, root: Path):
        self.root = root
        self.memory = load_yaml(root / "config" / "memory-config.yaml")
        self.scoring = load_yaml(root / "config" / "scoring-config.yaml")
        self.retention = load_yaml(root / "config" / "retention-policy.yaml")
        self.cleanup = load_yaml(root / "config" / "cleanup-policy.yaml")
        self._resolve_memory_paths()

    def _resolve_memory_paths(self) -> None:
        paths = self.memory.get("paths", {})
        for key, value in list(paths.items()):
            if not value:
                continue
            path = Path(value)
            if not path.is_absolute():
                paths[key] = str((self.root / path).resolve())
