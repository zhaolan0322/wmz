from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from memory_system_runtime import MemorySystemApp
from memory_system_runtime.core.models import RuntimeContext
from memory_system_runtime.core.utils import normalize_text, simple_query_type


REGISTRY_PATH = ROOT / "config" / "source-registry.yaml"
REPORT_PATH = ROOT / "openclaw_history_memory_report.md"


def load_registry() -> dict:
    if not REGISTRY_PATH.exists():
        return {"settings": {}, "projects": []}
    return yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8")) or {"settings": {}, "projects": []}


def load_session_index() -> dict[str, dict]:
    index_path = Path.home() / ".codex" / "session_index.jsonl"
    data: dict[str, dict] = {}
    if not index_path.exists():
        return data
    for line in index_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        data[item["id"]] = item
    return data


def locate_openclaw_sessions(openclaw_root: Path) -> list[dict]:
    session_root = Path.home() / ".codex" / "sessions"
    session_index = load_session_index()
    results: list[dict] = []
    for path in sorted(session_root.rglob("*.jsonl")):
        cwd = ""
        session_id = ""
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            item = json.loads(raw_line)
            if item.get("type") == "session_meta":
                payload = item.get("payload", {})
                cwd = payload.get("cwd", "")
                session_id = payload.get("id", "")
                break
        if not cwd or not session_id:
            continue
        cwd_path = Path(cwd)
        try:
            cwd_path.relative_to(openclaw_root)
            in_scope = True
        except ValueError:
            in_scope = False
        if not in_scope:
            continue
        results.append(
            {
                "session_id": session_id,
                "thread_name": session_index.get(session_id, {}).get("thread_name", ""),
                "cwd": str(cwd_path),
                "path": str(path),
            }
        )
    return results


def resolve_project_path(openclaw_root: Path, cwd: Path) -> Path:
    try:
        relative = cwd.relative_to(openclaw_root)
    except ValueError:
        return openclaw_root
    if not relative.parts:
        return openclaw_root
    first = relative.parts[0]
    if first in {".", ""}:
        return openclaw_root
    return openclaw_root / first


def auto_import_sessions(openclaw_root: Path, sessions: list[dict]) -> list[dict]:
    imported: list[dict] = []
    for session in sessions:
        cwd = Path(session["cwd"])
        project_id = infer_project_id(openclaw_root, cwd)
        project_path = resolve_project_path(openclaw_root, cwd)
        command = [
            sys.executable,
            str(ROOT / "scripts" / "import_codex_session.py"),
            "--session-id",
            session["session_id"],
            "--project-id",
            project_id or "openclaw",
            "--project-path",
            str(project_path),
        ]
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
        payload = json.loads(proc.stdout)
        imported.append(
            {
                "session_id": session["session_id"],
                "project_id": project_id or "openclaw",
                "project_path": str(project_path),
                "imported_memory_ids": payload.get("imported_memory_ids", []),
            }
        )
    return imported


def sanitize_user_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"# AGENTS\.md instructions[\s\S]*?</INSTRUCTIONS>", "", text)
    text = re.sub(r"<environment_context>[\s\S]*?</environment_context>", "", text)
    text = normalize_text(text)
    return text.strip()


def extract_user_turns(session_path: Path) -> list[str]:
    turns: list[str] = []
    for raw_line in session_path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        item = json.loads(raw_line)
        if item.get("type") != "response_item":
            continue
        payload = item.get("payload", {})
        if payload.get("type") != "message" or payload.get("role") != "user":
            continue
        parts: list[str] = []
        for content in payload.get("content", []):
            text = content.get("text") or content.get("input_text") or content.get("output_text")
            if text:
                parts.append(text)
        text = sanitize_user_text("\n".join(parts))
        if not text:
            continue
        turns.append(text)
    return turns


def infer_project_id(openclaw_root: Path, cwd: Path) -> str | None:
    try:
        relative = cwd.relative_to(openclaw_root)
    except ValueError:
        return None
    if not relative.parts:
        return "openclaw"
    first = relative.parts[0]
    if first in {".", ""}:
        return "openclaw"
    return first.lower().replace("_", "-").replace(" ", "-")


def memory_needed(query_type: str, query: str) -> bool:
    if query_type in {"task_continue", "problem_blocked", "historical_lookup", "project_planning", "exact_recall"}:
        return True
    q = query.lower()
    return any(token in q for token in ["继续", "上次", "之前", "经验", "回忆", "怎么做", "如何", "先看什么"])


def progress_bar(score: float, width: int = 20) -> str:
    score = max(0.0, min(1.0, score))
    filled = round(score * width)
    return "█" * filled + "░" * (width - filled)


def main() -> None:
    registry = load_registry()
    openclaw_root = Path(
        registry.get("settings", {}).get("openclaw_root")
        or (ROOT / "openclaw")
    )
    sessions = locate_openclaw_sessions(openclaw_root)
    imported_sessions = auto_import_sessions(openclaw_root, sessions)

    app = MemorySystemApp(ROOT)
    app.initialize()
    memories = {memory.memory_id: memory for memory in app.store.load_memories(active_only=True)}

    results: list[dict] = []
    total_turns = 0
    eligible_turns = 0
    memory_needed_turns = 0
    memory_hit_turns = 0
    same_scope_turns = 0
    memory_used_turns = 0
    used_memory_total = 0
    query_type_counter: dict[str, int] = {}

    for session in sessions:
        session_path = Path(session["path"])
        cwd = Path(session["cwd"])
        project_id = infer_project_id(openclaw_root, cwd)
        for turn in extract_user_turns(session_path):
            total_turns += 1
            query_type = simple_query_type(turn)
            query_type_counter[query_type] = query_type_counter.get(query_type, 0) + 1
            if len(turn) < 4:
                continue
            eligible_turns += 1
            needs_memory = memory_needed(query_type, turn)
            if needs_memory:
                memory_needed_turns += 1
            context = RuntimeContext(
                query_id=str(uuid4()),
                session_id=session["session_id"],
                project_id=project_id,
                explicit_recall_requested=("上次" in turn or "之前" in turn or "回忆" in turn or "继续" in turn),
                delivery_level_ceiling=4 if query_type == "exact_recall" else 2,
                retrieval_cost_budget=10,
                context_token_budget=800,
            )
            output = app.handle_query(turn, context)
            used_ids = output.get("used_memory_ids", [])
            if used_ids:
                memory_used_turns += 1
                used_memory_total += len(used_ids)
            if needs_memory and used_ids:
                memory_hit_turns += 1
            if project_id and used_ids:
                target_scope = f"project:{project_id}"
                if any(memories.get(memory_id) and memories[memory_id].scope == target_scope for memory_id in used_ids):
                    same_scope_turns += 1
            results.append(
                {
                    "session_id": session["session_id"],
                    "thread_name": session["thread_name"],
                    "cwd": session["cwd"],
                    "project_id": project_id,
                    "query": turn,
                    "query_type": query_type,
                    "memory_needed": needs_memory,
                    "memory_used": bool(used_ids),
                    "delivery_level": output["delivery_level"],
                    "used_memory_ids": used_ids,
                    "response_preview": output["response"][:160],
                }
            )

    history_metrics = {
        "session_count": len(sessions),
        "total_turns": total_turns,
        "eligible_turns": eligible_turns,
        "memory_needed_turns": memory_needed_turns,
        "memory_hit_turns": memory_hit_turns,
        "memory_hit_rate": round(memory_hit_turns / memory_needed_turns, 3) if memory_needed_turns else 0.0,
        "memory_used_rate": round(memory_used_turns / eligible_turns, 3) if eligible_turns else 0.0,
        "same_scope_hit_rate": round(same_scope_turns / memory_used_turns, 3) if memory_used_turns else 0.0,
        "avg_used_memory_count": round(used_memory_total / memory_used_turns, 3) if memory_used_turns else 0.0,
        "query_type_distribution": query_type_counter,
    }

    lines: list[str] = []
    lines.append("# openclaw 对话历史记忆回放报告")
    lines.append("")
    lines.append("## 1. 核心指标")
    lines.append("")
    lines.append(f"- 会话数：`{history_metrics['session_count']}`")
    lines.append(f"- 总用户轮次：`{history_metrics['total_turns']}`")
    lines.append(f"- 有效轮次：`{history_metrics['eligible_turns']}`")
    lines.append(f"- 判定需要记忆的轮次：`{history_metrics['memory_needed_turns']}`")
    lines.append(f"- 命中记忆的轮次：`{history_metrics['memory_hit_turns']}`")
    lines.append(f"- 记忆命中率：`{history_metrics['memory_hit_rate']:.3f}` {progress_bar(history_metrics['memory_hit_rate'])}")
    lines.append(f"- 记忆使用率：`{history_metrics['memory_used_rate']:.3f}` {progress_bar(history_metrics['memory_used_rate'])}")
    lines.append(f"- 同 scope 命中率：`{history_metrics['same_scope_hit_rate']:.3f}` {progress_bar(history_metrics['same_scope_hit_rate'])}")
    lines.append(f"- 平均每次使用记忆数：`{history_metrics['avg_used_memory_count']:.3f}`")
    lines.append(f"- 自动导入会话数：`{len(imported_sessions)}`")
    lines.append("")
    lines.append("## 2. query_type 分布")
    lines.append("")
    for key, value in sorted(history_metrics["query_type_distribution"].items()):
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    lines.append("## 3. 对话回放明细")
    lines.append("")
    lines.append("| session_id | 项目 | query_type | need_memory | memory_used | delivery | used_memory_ids | query |")
    lines.append("|---|---|---|---|---|---:|---|---|")
    for item in results:
        lines.append(
            f"| {item['session_id']} | {item['project_id'] or '-'} | {item['query_type']} | "
            f"{'Y' if item['memory_needed'] else 'N'} | {'Y' if item['memory_used'] else 'N'} | "
            f"{item['delivery_level']} | "
            f"{', '.join(item['used_memory_ids']) if item['used_memory_ids'] else '-'} | "
            f"{item['query'][:48].replace('|', ' ')} |"
        )
    lines.append("")
    lines.append("## 4. 结论怎么读")
    lines.append("")
    lines.append("- 你这次要看的核心不是项目文档，而是每条历史 query 回放后有没有命中 `used_memory_ids`。")
    lines.append("- `memory_hit_rate` 看的是：在应该用记忆的对话里，系统有没有真的调到记忆。")
    lines.append("- `same_scope_hit_rate` 看的是：如果 query 带项目上下文，命中的是不是对应 scope 的记忆。")
    lines.append("- `avg_used_memory_count` 太高说明虽然命中了，但输出可能开始变重。")
    lines.append("- 回放前会先自动导入 `openclaw` 真实对话历史，所以这里测的是最新对话，不需要手动先导入。")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "ok",
                "report_path": str(REPORT_PATH),
                "imported_sessions": imported_sessions,
                "metrics": history_metrics,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
