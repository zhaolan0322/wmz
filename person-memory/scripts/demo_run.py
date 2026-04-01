from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from memory_system_runtime import MemorySystemApp
from memory_system_runtime.core.models import RuntimeContext


def run_demo() -> None:
    app = MemorySystemApp(ROOT)
    app.initialize()
    demos = [
        (
            "这个 sync pipeline 的问题和之前很像，我现在卡住了，先该检查什么？",
            RuntimeContext(
                query_id=str(uuid4()),
                session_id=str(uuid4()),
                project_id="sync-engine",
                task_id="task-sync-1",
                delivery_level_ceiling=3,
            ),
        ),
        (
            "我准备开始一个新的研究任务，怎么起步更高效？",
            RuntimeContext(
                query_id=str(uuid4()),
                session_id=str(uuid4()),
                project_id="research",
                task_id="task-research-1",
                delivery_level_ceiling=2,
            ),
        ),
        (
            "你好",
            RuntimeContext(query_id=str(uuid4()), session_id=str(uuid4())),
        ),
    ]
    outputs = []
    for query, context in demos:
        result = app.handle_query(query, context)
        outputs.append(result)
    print(json.dumps(outputs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run_demo()
