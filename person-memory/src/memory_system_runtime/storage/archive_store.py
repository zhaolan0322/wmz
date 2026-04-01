from __future__ import annotations

from pathlib import Path


class ArchiveStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def write_text(self, relative_path: str, content: str) -> str:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(path)

    def read_text(self, absolute_or_relative: str) -> str:
        path = Path(absolute_or_relative)
        if not path.is_absolute():
            path = self.root / absolute_or_relative
        return path.read_text(encoding="utf-8")
