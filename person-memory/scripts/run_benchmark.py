from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from memory_system_runtime import MemorySystemApp
from memory_system_runtime.core.config import ConfigBundle
from memory_system_runtime.evaluation.benchmark_runner import BenchmarkRunner


def main() -> None:
    config = ConfigBundle(ROOT)
    db_path = Path(config.memory["paths"]["metadata_db"])
    trace_path = Path(config.memory["paths"]["trace_log"])

    with tempfile.TemporaryDirectory(prefix="memory-benchmark-backup-") as tmpdir:
        backup_root = Path(tmpdir)
        db_backup = backup_root / "metadata.db"
        trace_backup = backup_root / "decision_trace.jsonl"
        if db_path.exists():
            shutil.copy2(db_path, db_backup)
        if trace_path.exists():
            trace_backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(trace_path, trace_backup)

        try:
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "init_db.py")],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "memory_cli.py"), "sync"],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            app = MemorySystemApp(ROOT)
            app.initialize()
            runner = BenchmarkRunner(app, ROOT / "data" / "benchmark_cases")
            result = runner.run()
        finally:
            if db_backup.exists():
                db_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(db_backup, db_path)
            if trace_backup.exists():
                trace_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(trace_backup, trace_path)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
