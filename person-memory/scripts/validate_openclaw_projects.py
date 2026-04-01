from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import uuid4

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from memory_system_runtime import MemorySystemApp
from memory_system_runtime.core.models import MemoryItem, RuntimeContext


REGISTRY_PATH = ROOT / "config" / "source-registry.yaml"


def load_registry() -> dict:
    if not REGISTRY_PATH.exists():
        return {"settings": {}, "projects": []}
    return yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8")) or {"settings": {}, "projects": []}


def project_memories(memories: list[MemoryItem], project_id: str) -> list[MemoryItem]:
    scope = f"project:{project_id}"
    return [memory for memory in memories if memory.scope == scope]


def find_memory(memories: list[MemoryItem], *, layer: str | None = None, title_contains: str | None = None, memory_type: str | None = None) -> MemoryItem | None:
    for memory in memories:
        if layer and memory.layer != layer:
            continue
        if memory_type and memory.memory_type != memory_type:
            continue
        if title_contains and title_contains not in memory.title:
            continue
        return memory
    return None


def build_cases(project: dict, memories: list[MemoryItem]) -> list[dict]:
    project_name = project["project_name"]
    entry = find_memory(memories, layer="core", memory_type="project_profile")
    overview = find_memory(memories, title_contains="项目概览")
    structure = find_memory(memories, layer="procedural")
    artifacts = find_memory(memories, title_contains="关键文件")
    cases: list[dict] = []

    if entry:
        cases.append(
            {
                "case_id": f"{project['project_id']}-ENTRY",
                "dimension": "entry",
                "query": f"{project_name} 项目开始时应该先看什么？",
                "expected_memory_id": entry.memory_id,
                "expected_delivery_level": 2,
            }
        )
    if overview:
        cases.append(
            {
                "case_id": f"{project['project_id']}-OVERVIEW",
                "dimension": "overview",
                "query": f"{project_name} 这个项目是做什么的？",
                "expected_memory_id": overview.memory_id,
                "expected_delivery_level": 2,
            }
        )
    if structure:
        cases.append(
            {
                "case_id": f"{project['project_id']}-STRUCTURE",
                "dimension": "structure",
                "query": f"{project_name} 的结构和进入顺序是什么？",
                "expected_memory_id": structure.memory_id,
                "expected_delivery_level": 2,
            }
        )
    if artifacts:
        cases.append(
            {
                "case_id": f"{project['project_id']}-ARTIFACTS",
                "dimension": "artifacts",
                "query": f"{project_name} 当前有哪些关键文件或产物？",
                "expected_memory_id": artifacts.memory_id,
                "expected_delivery_level": 2,
            }
        )

    return cases


def evaluate_project(app: MemorySystemApp, project: dict, all_memories: list[MemoryItem]) -> dict:
    project_scope = f"project:{project['project_id']}"
    scoped_memories = project_memories(all_memories, project["project_id"])
    memory_by_id = {memory.memory_id: memory for memory in all_memories}
    cases = build_cases(project, scoped_memories)
    results = []

    for case in cases:
        context = RuntimeContext(
            query_id=str(uuid4()),
            session_id=str(uuid4()),
            project_id=project["project_id"],
            explicit_recall_requested=True,
            delivery_level_ceiling=2,
            retrieval_cost_budget=10,
            context_token_budget=700,
        )
        output = app.handle_query(case["query"], context)
        used_ids = output.get("used_memory_ids", [])
        used_memories = [memory_by_id[item] for item in used_ids if item in memory_by_id]
        same_scope_ids = [memory.memory_id for memory in used_memories if memory.scope == project_scope]
        foreign_project_ids = [
            memory.memory_id
            for memory in used_memories
            if memory.scope.startswith("project:") and memory.scope != project_scope
        ]
        hit_expected = case["expected_memory_id"] in used_ids
        delivery_ok = output["delivery_level"] == case["expected_delivery_level"]
        pollution_free = not foreign_project_ids
        scope_precision = round(
            len(same_scope_ids) / len([memory for memory in used_memories if memory.scope.startswith("project:")]),
            3,
        ) if any(memory.scope.startswith("project:") for memory in used_memories) else 1.0
        passed = hit_expected and delivery_ok and pollution_free
        results.append(
            {
                "case_id": case["case_id"],
                "dimension": case["dimension"],
                "query": case["query"],
                "passed": passed,
                "expected_memory_id": case["expected_memory_id"],
                "used_memory_ids": used_ids,
                "same_scope_memory_ids": same_scope_ids,
                "foreign_project_memory_ids": foreign_project_ids,
                "hit_expected_memory": hit_expected,
                "delivery_ok": delivery_ok,
                "pollution_free": pollution_free,
                "scope_precision": scope_precision,
                "delivery_level": output["delivery_level"],
                "response_preview": output["response"][:160],
            }
        )

    total = len(results)
    passed = sum(1 for item in results if item["passed"])
    hit = sum(1 for item in results if item["hit_expected_memory"])
    pollution_free = sum(1 for item in results if item["pollution_free"])
    delivery_fit = sum(1 for item in results if item["delivery_ok"])
    avg_scope_precision = round(sum(item["scope_precision"] for item in results) / total, 3) if total else 0.0
    avg_used_memory_count = round(sum(len(item["used_memory_ids"]) for item in results) / total, 3) if total else 0.0

    optimization_hints: list[str] = []
    if total == 0:
        optimization_hints.append("当前项目还没有形成足够的项目记忆，先补 README、主说明文件或 SKILL.md 后再同步。")
    else:
        if hit < total:
            optimization_hints.append("项目命中率未满，优先加强项目入口摘要与结构摘要的关键词覆盖。")
        if pollution_free < total:
            optimization_hints.append("存在跨项目污染，应继续提高 project priority 和 same_scope_only 的放行权重。")
        if delivery_fit < total:
            optimization_hints.append("交付层级不稳定，建议继续收紧项目问答的默认 delivery ceiling。")
        if avg_used_memory_count > 2.0:
            optimization_hints.append("单次回答使用的记忆过多，建议进一步降低前台候选数量。")
        if not optimization_hints:
            optimization_hints.append("当前项目命中、隔离和交付都稳定，可以开始接入真实会话继续观察。")

    return {
        "project_id": project["project_id"],
        "project_name": project["project_name"],
        "project_path": project["project_path"],
        "memory_count": len(scoped_memories),
        "total_cases": total,
        "passed_cases": passed,
        "pass_rate": round(passed / total, 3) if total else 0.0,
        "project_hit_rate": round(hit / total, 3) if total else 0.0,
        "pollution_free_rate": round(pollution_free / total, 3) if total else 0.0,
        "delivery_fit_rate": round(delivery_fit / total, 3) if total else 0.0,
        "avg_scope_precision": avg_scope_precision,
        "avg_used_memory_count": avg_used_memory_count,
        "cases": results,
        "optimization_hints": optimization_hints,
    }


def main() -> None:
    registry = load_registry()
    openclaw_root = Path(
        registry.get("settings", {}).get("openclaw_root")
        or (ROOT / "openclaw")
    )
    app = MemorySystemApp(ROOT)
    app.initialize()
    memories = app.store.load_memories(active_only=True)

    openclaw_projects = []
    for project in registry.get("projects", []):
        project_path = Path(project.get("project_path", ""))
        if str(project_path).startswith(str(openclaw_root)) and project_path.exists():
            openclaw_projects.append(project)

    project_results = [evaluate_project(app, project, memories) for project in openclaw_projects]
    total_cases = sum(item["total_cases"] for item in project_results)
    passed_cases = sum(item["passed_cases"] for item in project_results)
    overall = {
        "project_count": len(project_results),
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "pass_rate": round(passed_cases / total_cases, 3) if total_cases else 0.0,
        "project_hit_rate": round(
            sum(item["project_hit_rate"] * item["total_cases"] for item in project_results) / total_cases,
            3,
        ) if total_cases else 0.0,
        "pollution_free_rate": round(
            sum(item["pollution_free_rate"] * item["total_cases"] for item in project_results) / total_cases,
            3,
        ) if total_cases else 0.0,
        "delivery_fit_rate": round(
            sum(item["delivery_fit_rate"] * item["total_cases"] for item in project_results) / total_cases,
            3,
        ) if total_cases else 0.0,
        "avg_scope_precision": round(
            sum(item["avg_scope_precision"] * item["total_cases"] for item in project_results) / total_cases,
            3,
        ) if total_cases else 0.0,
        "avg_used_memory_count": round(
            sum(item["avg_used_memory_count"] * item["total_cases"] for item in project_results) / total_cases,
            3,
        ) if total_cases else 0.0,
    }
    print(
        json.dumps(
            {
                "status": "ok",
                "openclaw_root": str(openclaw_root),
                "overall_metrics": overall,
                "project_results": project_results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
