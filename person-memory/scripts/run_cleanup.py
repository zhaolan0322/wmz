from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from memory_system_runtime import MemorySystemApp


def main() -> None:
    app = MemorySystemApp(ROOT)
    app.initialize()
    memories = app.store.load_memories(active_only=True)
    actions = []
    for memory in memories:
        priority = app.cleanup_engine.cleanup_priority(memory)
        action = app.cleanup_engine.decide_action(memory, priority)
        log = app.cleanup_engine.build_log(memory, action, priority)
        app.store.insert_cleanup_action(log)
        if action == "archive":
            app.store.update_status(memory.memory_id, "archived", "archive")
        elif action == "suppress":
            app.store.update_status(memory.memory_id, "stale")
        actions.append({"memory_id": memory.memory_id, "action": action, "priority": round(priority, 3)})
    print(json.dumps(actions, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
