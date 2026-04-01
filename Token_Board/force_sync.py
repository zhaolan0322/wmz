import json
import os
from datetime import datetime, timezone
from pathlib import Path


def discover_agents_root() -> Path:
    candidates = []
    for env_name in ("TOKEN_BOARD_AGENTS_ROOT", "OPENCLAW_AGENTS_ROOT"):
        raw = os.getenv(env_name, "").strip()
        if raw:
            candidates.append(Path(raw).expanduser())
    candidates.extend([
        Path("/state/agents"),
        Path.home() / ".openclaw" / "agents",
    ])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def sync_all_agents():
    project_root = Path(__file__).resolve().parent
    base_dir = discover_agents_root()
    project_data_dir = project_root / "data"
    project_data_dir.mkdir(parents=True, exist_ok=True)

    for agent_dir in base_dir.iterdir():
        if not agent_dir.is_dir():
            continue
        session_path = agent_dir / "sessions" / "sessions.json"
        if not session_path.exists():
            continue
        target_path = project_data_dir / f"{agent_dir.name}_sessions.json"
        with session_path.open("r", encoding="utf-8") as source:
            data = json.load(source)
        with target_path.open("w", encoding="utf-8") as target:
            json.dump(data, target, ensure_ascii=False)
        print(f"同步成功: {agent_dir.name}")

    timestamp = datetime.now(timezone.utc).isoformat()
    progress_path = project_root / "PROGRESS.md"
    with progress_path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n- [{timestamp}] 手动触发强制同步，数据已刷新至最新。")


if __name__ == "__main__":
    sync_all_agents()
