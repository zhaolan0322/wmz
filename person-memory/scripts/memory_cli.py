from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from memory_system_runtime import MemorySystemApp
from memory_system_runtime.core.config import ConfigBundle
from memory_system_runtime.core.models import RuntimeContext


REGISTRY_PATH = ROOT / "config" / "source-registry.yaml"
WATCH_LOG_PATH = ROOT / "data" / "runtime_data" / "memory" / "logs" / "openclaw_watch.log"
WATCH_PID_PATH = ROOT / "data" / "runtime_data" / "memory" / "logs" / "openclaw_watch.pid"


def load_registry() -> dict:
    if not REGISTRY_PATH.exists():
        return {"settings": {}, "projects": []}
    return yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8")) or {"settings": {}, "projects": []}


def save_registry(registry: dict) -> None:
    REGISTRY_PATH.write_text(yaml.safe_dump(registry, allow_unicode=True, sort_keys=False), encoding="utf-8")


def run_script(script_name: str, *args: str) -> dict:
    command = [sys.executable, str(ROOT / "scripts" / script_name), *args]
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
    output = proc.stdout.strip()
    if not output:
        return {"status": "ok"}
    return json.loads(output)


def watch_process_alive(pid: int) -> bool:
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        f"if (Get-Process -Id {pid} -ErrorAction SilentlyContinue) {{ 'alive' }} else {{ 'dead' }}",
    ]
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
    return proc.stdout.strip() == "alive"


def choose_import_script(project_path: str) -> str:
    path = Path(project_path)
    if (path / "SKILL.md").exists() or (path / "references" / "prompt-templates.md").exists():
        return "import_project_docs.py"
    return "import_generic_project.py"


def resolve_project_id(project_id: str | None, registry: dict) -> str | None:
    if project_id:
        return project_id
    return registry.get("settings", {}).get("default_project_id")


def find_project(project_id: str, registry: dict) -> dict | None:
    for project in registry.get("projects", []):
        if project.get("project_id") == project_id:
            return project
    return None


def cmd_init(_: argparse.Namespace) -> None:
    result = run_script("init_db.py")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_register_project(args: argparse.Namespace) -> None:
    registry = load_registry()
    projects = registry.setdefault("projects", [])
    existing = find_project(args.project_id, registry)
    record = {
        "project_id": args.project_id,
        "project_name": args.project_name,
        "project_path": args.project_path,
        "session_ids": args.session_ids or [],
    }
    if existing:
        existing.update(record)
    else:
        projects.append(record)
    if args.set_default:
        registry.setdefault("settings", {})["default_project_id"] = args.project_id
    save_registry(registry)
    print(
        json.dumps(
            {
                "status": "ok",
                "message": "项目已登记到 source-registry.yaml",
                "project": record,
                "default_project_id": registry.get("settings", {}).get("default_project_id"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_sync(args: argparse.Namespace) -> None:
    registry = load_registry()
    projects = registry.get("projects", [])
    if args.project_id:
        projects = [project for project in projects if project.get("project_id") == args.project_id]
    results = []
    for project in projects:
        project_result = {
            "project_id": project["project_id"],
            "project_name": project["project_name"],
            "imports": [],
        }
        import_script = choose_import_script(project["project_path"])
        project_result["imports"].append(
            run_script(
                import_script,
                "--project-id",
                project["project_id"],
                "--project-name",
                project["project_name"],
                "--project-path",
                project["project_path"],
            )
        )
        for session_id in project.get("session_ids", []):
            project_result["imports"].append(
                run_script(
                    "import_codex_session.py",
                    "--session-id",
                    session_id,
                    "--project-id",
                    project["project_id"],
                    "--project-path",
                    project["project_path"],
                )
            )
        results.append(project_result)
    print(
        json.dumps(
            {
                "status": "ok",
                "synced_projects": len(results),
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_import_project(args: argparse.Namespace) -> None:
    import_script = choose_import_script(args.project_path)
    result = run_script(
        import_script,
        "--project-id",
        args.project_id,
        "--project-name",
        args.project_name,
        "--project-path",
        args.project_path,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_import_session(args: argparse.Namespace) -> None:
    registry = load_registry()
    project_id = resolve_project_id(args.project_id, registry)
    project_path = args.project_path
    if project_id and not project_path:
        project = find_project(project_id, registry)
        if project:
            project_path = project.get("project_path")
    cli_args = ["--session-id", args.session_id]
    if project_id:
        cli_args += ["--project-id", project_id]
    if args.task_id:
        cli_args += ["--task-id", args.task_id]
    if project_path:
        cli_args += ["--project-path", project_path]
    result = run_script("import_codex_session.py", *cli_args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_ask(args: argparse.Namespace) -> None:
    registry = load_registry()
    app = MemorySystemApp(ROOT)
    app.initialize()
    project_id = resolve_project_id(args.project_id, registry)
    context = RuntimeContext(
        query_id=str(uuid4()),
        session_id=args.session_id or str(uuid4()),
        project_id=project_id,
        task_id=args.task_id,
        explicit_recall_requested=args.explicit_recall,
        delivery_level_ceiling=args.delivery_level_ceiling,
        retrieval_cost_budget=args.retrieval_cost_budget,
        context_token_budget=args.context_token_budget,
    )
    result = app.handle_query(args.query, context)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_status(_: argparse.Namespace) -> None:
    registry = load_registry()
    app = MemorySystemApp(ROOT)
    app.initialize()
    memories = app.store.load_memories(active_only=False)
    by_layer: dict[str, int] = {}
    by_scope: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for memory in memories:
        by_layer[memory.layer] = by_layer.get(memory.layer, 0) + 1
        by_scope[memory.scope] = by_scope.get(memory.scope, 0) + 1
        by_status[memory.status] = by_status.get(memory.status, 0) + 1
    trace_path = ROOT / "data" / "runtime_data" / "memory" / "logs" / "decision_trace.jsonl"
    trace_count = 0
    memory_used_count = 0
    if trace_path.exists():
        for line in trace_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            trace_count += 1
            payload = json.loads(line)
            if payload.get("final_outcome", {}).get("memory_used"):
                memory_used_count += 1
    print(
        json.dumps(
            {
                "status": "ok",
                "default_project_id": registry.get("settings", {}).get("default_project_id"),
                "registered_projects": registry.get("projects", []),
                "memory_counts": {
                    "total": len(memories),
                    "by_layer": by_layer,
                    "by_scope": by_scope,
                    "by_status": by_status,
                },
                "trace_summary": {
                    "trace_count": trace_count,
                    "memory_used_rate": round(memory_used_count / trace_count, 3) if trace_count else 0.0,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_find_sessions(args: argparse.Namespace) -> None:
    registry = load_registry()
    codex_home = Path(registry.get("settings", {}).get("codex_home", Path.home() / ".codex"))
    index_path = codex_home / "session_index.jsonl"
    results = []
    if index_path.exists():
        keyword = (args.keyword or "").lower()
        for line in index_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            thread_name = item.get("thread_name", "")
            if keyword and keyword not in thread_name.lower():
                continue
            results.append(
                {
                    "session_id": item.get("id"),
                    "thread_name": thread_name,
                    "updated_at": item.get("updated_at"),
                }
            )
    results.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
    print(json.dumps({"status": "ok", "count": len(results), "results": results[: args.limit]}, ensure_ascii=False, indent=2))


def cmd_review(args: argparse.Namespace) -> None:
    app = MemorySystemApp(ROOT)
    app.initialize()
    memories = app.store.load_memories(active_only=True)
    items = []
    for memory in memories:
        priority = app.cleanup_engine.cleanup_priority(memory)
        items.append(
            {
                "memory_id": memory.memory_id,
                "title": memory.title,
                "scope": memory.scope,
                "layer": memory.layer,
                "status": memory.status,
                "cleanup_priority": round(priority, 3),
                "suggested_action": app.cleanup_engine.decide_action(memory, priority),
            }
        )
    items.sort(key=lambda item: item["cleanup_priority"], reverse=True)
    print(json.dumps({"status": "ok", "top_items": items[: args.limit]}, ensure_ascii=False, indent=2))


def cmd_cleanup(_: argparse.Namespace) -> None:
    result = run_script("run_cleanup.py")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_integrity(_: argparse.Namespace) -> None:
    result = run_script("check_integrity.py")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_benchmark(_: argparse.Namespace) -> None:
    result = run_script("run_benchmark.py")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_scan_openclaw(args: argparse.Namespace) -> None:
    registry = load_registry()
    app = MemorySystemApp(ROOT)
    app.initialize()
    openclaw_root = Path(
        args.openclaw_root
        or registry.get("settings", {}).get("openclaw_root")
        or (ROOT / "openclaw")
    )
    openclaw_root.mkdir(parents=True, exist_ok=True)
    discovered = []
    updated = []
    projects = registry.setdefault("projects", [])
    stale_project_ids = []
    kept_projects = []
    for project in projects:
        project_path = Path(project.get("project_path", ""))
        if str(project_path).startswith(str(openclaw_root)) and not project_path.exists():
            stale_project_ids.append(project.get("project_id"))
            app.store.delete_memories_by_scope(f"project:{project.get('project_id')}")
            project_archive_dir = ROOT / "data" / "runtime_data" / "memory" / "archive" / "projects" / str(project.get("project_id"))
            if project_archive_dir.exists():
                shutil.rmtree(project_archive_dir)
            continue
        kept_projects.append(project)
    registry["projects"] = kept_projects
    if registry.get("settings", {}).get("default_project_id") in stale_project_ids:
        registry.setdefault("settings", {})["default_project_id"] = None
    projects = registry["projects"]
    existing_ids = {project.get("project_id") for project in projects}
    for child in sorted(openclaw_root.iterdir()):
        if not child.is_dir():
            continue
        project_id = child.name.lower().replace("_", "-").replace(" ", "-")
        project_name = child.name
        if project_id not in existing_ids:
            projects.append(
                {
                    "project_id": project_id,
                    "project_name": project_name,
                    "project_path": str(child),
                    "session_ids": [],
                }
            )
            existing_ids.add(project_id)
            updated.append(project_id)
        discovered.append(
            {
                "project_id": project_id,
                "project_name": project_name,
                "project_path": str(child),
                "import_script": choose_import_script(str(child)),
            }
        )
    save_registry(registry)
    result = {
        "status": "ok",
        "openclaw_root": str(openclaw_root),
        "discovered_count": len(discovered),
        "newly_registered": updated,
        "removed_stale": stale_project_ids,
        "projects": discovered,
    }
    if args.sync:
        sync_result = run_script("memory_cli.py", "sync")
        result["sync_result"] = sync_result
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_validate_openclaw(_: argparse.Namespace) -> None:
    result = run_script("validate_openclaw_projects.py")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_replay_openclaw_history(_: argparse.Namespace) -> None:
    result = run_script("replay_openclaw_history.py")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_report_openclaw(args: argparse.Namespace) -> None:
    registry = load_registry()
    openclaw_root = Path(
        args.openclaw_root
        or registry.get("settings", {}).get("openclaw_root")
        or (ROOT / "openclaw")
    )
    scan_result = run_script("memory_cli.py", "scan-openclaw", "--sync")
    validation_result = run_script("validate_openclaw_projects.py")
    benchmark_result = run_script("memory_cli.py", "benchmark")
    status_result = run_script("memory_cli.py", "status")
    report_path = ROOT / "openclaw_memory_observation_report.md"
    lines = []
    lines.append("# OpenClaw 记忆观察报告")
    lines.append("")
    lines.append(f"- 观察根目录：`{openclaw_root}`")
    lines.append(f"- 发现项目数：`{scan_result['discovered_count']}`")
    lines.append(f"- 新注册项目：`{len(scan_result.get('newly_registered', []))}`")
    lines.append(f"- 当前 benchmark 通过率：`{benchmark_result['pass_rate']:.3f}`")
    lines.append(f"- openclaw 项目验证通过率：`{validation_result['overall_metrics']['pass_rate']:.3f}`")
    lines.append("")
    lines.append("## 发现的项目")
    lines.append("")
    if scan_result["projects"]:
        lines.append("| Project ID | 项目名 | 导入方式 | 路径 |")
        lines.append("|---|---|---|---|")
        for project in scan_result["projects"]:
            script_name = project["import_script"].replace(".py", "")
            lines.append(f"| {project['project_id']} | {project['project_name']} | {script_name} | {project['project_path']} |")
    else:
        lines.append("- 当前 openclaw 下还没有可导入项目。")
    lines.append("")
    lines.append("## openclaw 项目级验证指标")
    lines.append("")
    overall = validation_result["overall_metrics"]
    lines.append(f"- 项目数：`{overall['project_count']}`")
    lines.append(f"- 项目级验证用例数：`{overall['total_cases']}`")
    lines.append(f"- 项目命中率：`{overall['project_hit_rate']:.3f}`")
    lines.append(f"- 污染抑制率：`{overall['pollution_free_rate']:.3f}`")
    lines.append(f"- 交付匹配率：`{overall['delivery_fit_rate']:.3f}`")
    lines.append(f"- 平均同 scope 精度：`{overall['avg_scope_precision']:.3f}`")
    lines.append(f"- 平均单次使用记忆数：`{overall['avg_used_memory_count']:.3f}`")
    lines.append("")
    if validation_result["project_results"]:
        lines.append("| Project ID | 项目命中率 | 污染抑制率 | 交付匹配率 | 平均同 Scope 精度 | 平均使用记忆数 |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for item in validation_result["project_results"]:
            lines.append(
                f"| {item['project_id']} | {item['project_hit_rate']:.3f} | {item['pollution_free_rate']:.3f} | "
                f"{item['delivery_fit_rate']:.3f} | {item['avg_scope_precision']:.3f} | {item['avg_used_memory_count']:.3f} |"
            )
        lines.append("")
        lines.append("## 主要问题与优化建议")
        lines.append("")
        for item in validation_result["project_results"]:
            lines.append(f"### {item['project_name']}")
            for hint in item["optimization_hints"]:
                lines.append(f"- {hint}")
            failed_cases = [case for case in item["cases"] if not case["passed"]]
            if failed_cases:
                lines.append("- 失败用例：")
                for case in failed_cases:
                    lines.append(
                        f"  - `{case['case_id']}`：命中={case['hit_expected_memory']}，污染={not case['pollution_free']}，交付层级={case['delivery_level']}"
                    )
            lines.append("")
    else:
        lines.append("- 当前没有 openclaw 真实项目验证结果。")
        lines.append("")

    lines.append("## Memory 结果摘要")
    lines.append("")
    lines.append(f"- 注册项目数：`{len(status_result['registered_projects'])}`")
    lines.append(f"- 活跃记忆总数：`{status_result['memory_counts']['total']}`")
    lines.append(f"- 记忆使用率：`{status_result['trace_summary']['memory_used_rate']:.3f}`")
    lines.append("")
    lines.append("## 当前优化建议")
    lines.append("")
    if not scan_result["projects"]:
        lines.append("- 先在 openclaw 下创建至少一个真实项目目录，再运行 `python scripts/memory_cli.py report-openclaw`。")
    else:
        lines.append("- 新项目创建后，优先补 README 或主说明文件，这样通用导入器能生成更高质量的项目入口摘要。")
        lines.append("- 如果项目开始产生真实会话，使用 `find-sessions` 找到对应 session_id，并补到 registry，再 `sync`。")
        lines.append("- 重点看项目命中率、污染抑制率、平均同 scope 精度；这三个比通用 benchmark 更能反映真实项目效果。")
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": "ok", "report_path": str(report_path)}, ensure_ascii=False, indent=2))


def cmd_dashboard(_: argparse.Namespace) -> None:
    result = run_script("generate_metrics_dashboard.py")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_observe_openclaw(args: argparse.Namespace) -> None:
    scan_result = run_script("memory_cli.py", "scan-openclaw", "--sync")
    validate_result = run_script("memory_cli.py", "validate-openclaw")
    history_result = run_script("memory_cli.py", "replay-openclaw-history")
    report_result = run_script("memory_cli.py", "report-openclaw")
    dashboard_result = run_script("generate_metrics_dashboard.py")
    print(
        json.dumps(
            {
                "status": "ok",
                "scan_result": scan_result,
                "validate_result": validate_result,
                "history_result": history_result,
                "report_path": report_result["report_path"],
                "dashboard_path": dashboard_result["report_path"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_watch_openclaw(args: argparse.Namespace) -> None:
    import time

    registry = load_registry()
    openclaw_root = Path(
        args.openclaw_root
        or registry.get("settings", {}).get("openclaw_root")
        or (ROOT / "openclaw")
    )
    openclaw_root.mkdir(parents=True, exist_ok=True)
    seen_projects = {child.name for child in openclaw_root.iterdir() if child.is_dir()}
    codex_home = Path(registry.get("settings", {}).get("codex_home", Path.home() / ".codex"))
    sessions_root = codex_home / "sessions"
    seen_sessions = {
        f"{item.as_posix()}::{item.stat().st_mtime_ns}"
        for item in sessions_root.rglob("*.jsonl")
    } if sessions_root.exists() else set()
    print(json.dumps({"status": "watching", "openclaw_root": str(openclaw_root), "interval_seconds": args.interval}, ensure_ascii=False))
    while True:
        current_projects = {child.name for child in openclaw_root.iterdir() if child.is_dir()}
        current_sessions = {
            f"{item.as_posix()}::{item.stat().st_mtime_ns}"
            for item in sessions_root.rglob("*.jsonl")
        } if sessions_root.exists() else set()
        new_dirs = sorted(current_projects - seen_projects)
        session_changed = current_sessions != seen_sessions
        if new_dirs or session_changed:
            print(
                json.dumps(
                    {
                        "status": "change_detected",
                        "new_projects": new_dirs,
                        "session_changed": session_changed,
                    },
                    ensure_ascii=False,
                )
            )
            _ = run_script("memory_cli.py", "scan-openclaw", "--sync")
            history = run_script("memory_cli.py", "replay-openclaw-history")
            report = run_script("memory_cli.py", "report-openclaw")
            dashboard = run_script("generate_metrics_dashboard.py")
            print(
                json.dumps(
                    {
                        "status": "report_updated",
                        "history_hit_rate": history.get("metrics", {}).get("memory_hit_rate"),
                        "report_path": report["report_path"],
                        "dashboard_path": dashboard["report_path"],
                    },
                    ensure_ascii=False,
                )
            )
            seen_projects = current_projects
            seen_sessions = current_sessions
        time.sleep(args.interval)


def cmd_start_watch_openclaw(args: argparse.Namespace) -> None:
    WATCH_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if WATCH_PID_PATH.exists():
        existing_pid = int(WATCH_PID_PATH.read_text(encoding="utf-8").strip())
        if watch_process_alive(existing_pid):
            print(
                json.dumps(
                    {
                        "status": "already_running",
                        "pid": existing_pid,
                        "log_path": str(WATCH_LOG_PATH),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return
        WATCH_PID_PATH.unlink(missing_ok=True)

    command = [
        "powershell",
        "-NoProfile",
        "-WindowStyle",
        "Hidden",
        "-Command",
        (
            f"Set-Location '{ROOT}'; "
            f"python scripts/memory_cli.py watch-openclaw --interval {args.interval} "
            f"*>> '{WATCH_LOG_PATH}'"
        ),
    ]
    proc = subprocess.Popen(command, cwd=ROOT, creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
    WATCH_PID_PATH.write_text(str(proc.pid), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "started",
                "pid": proc.pid,
                "interval_seconds": args.interval,
                "log_path": str(WATCH_LOG_PATH),
                "pid_path": str(WATCH_PID_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_stop_watch_openclaw(_: argparse.Namespace) -> None:
    if not WATCH_PID_PATH.exists():
        print(json.dumps({"status": "not_running"}, ensure_ascii=False, indent=2))
        return
    pid = int(WATCH_PID_PATH.read_text(encoding="utf-8").strip())
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue",
        ],
        cwd=ROOT,
        check=True,
    )
    WATCH_PID_PATH.unlink(missing_ok=True)
    print(json.dumps({"status": "stopped", "pid": pid}, ensure_ascii=False, indent=2))


def cmd_watch_status(_: argparse.Namespace) -> None:
    if not WATCH_PID_PATH.exists():
        print(
            json.dumps(
                {
                    "status": "not_running",
                    "log_path": str(WATCH_LOG_PATH),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    pid = int(WATCH_PID_PATH.read_text(encoding="utf-8").strip())
    alive = watch_process_alive(pid)
    if not alive:
        WATCH_PID_PATH.unlink(missing_ok=True)
    tail = ""
    if WATCH_LOG_PATH.exists():
        tail_lines = WATCH_LOG_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()[-8:]
        tail = "\n".join(tail_lines)
    print(
        json.dumps(
            {
                "status": "running" if alive else "stale_pid",
                "pid": pid,
                "alive": alive,
                "log_path": str(WATCH_LOG_PATH),
                "log_tail": tail,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="个人分层 AI 记忆系统统一 CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    init_parser = sub.add_parser("init", help="初始化数据库、保护层和样例数据")
    init_parser.set_defaults(func=cmd_init)

    register_parser = sub.add_parser("register-project", help="登记项目到 source-registry.yaml")
    register_parser.add_argument("--project-id", required=True)
    register_parser.add_argument("--project-name", required=True)
    register_parser.add_argument("--project-path", required=True)
    register_parser.add_argument("--session-ids", nargs="*", default=[])
    register_parser.add_argument("--set-default", action="store_true")
    register_parser.set_defaults(func=cmd_register_project)

    sync_parser = sub.add_parser("sync", help="按 source-registry.yaml 自动同步项目文档和会话")
    sync_parser.add_argument("--project-id", default=None)
    sync_parser.set_defaults(func=cmd_sync)

    import_project_parser = sub.add_parser("import-project", help="导入项目文档为项目记忆")
    import_project_parser.add_argument("--project-id", required=True)
    import_project_parser.add_argument("--project-name", required=True)
    import_project_parser.add_argument("--project-path", required=True)
    import_project_parser.set_defaults(func=cmd_import_project)

    import_session_parser = sub.add_parser("import-session", help="导入 Codex 会话为真实记忆")
    import_session_parser.add_argument("--session-id", required=True)
    import_session_parser.add_argument("--project-id", default=None)
    import_session_parser.add_argument("--project-path", default=None)
    import_session_parser.add_argument("--task-id", default=None)
    import_session_parser.set_defaults(func=cmd_import_session)

    ask_parser = sub.add_parser("ask", help="用当前记忆系统执行一次查询")
    ask_parser.add_argument("--query", required=True)
    ask_parser.add_argument("--project-id", default=None)
    ask_parser.add_argument("--task-id", default=None)
    ask_parser.add_argument("--session-id", default=None)
    ask_parser.add_argument("--explicit-recall", action="store_true")
    ask_parser.add_argument("--delivery-level-ceiling", type=int, default=2)
    ask_parser.add_argument("--retrieval-cost-budget", type=int, default=10)
    ask_parser.add_argument("--context-token-budget", type=int, default=800)
    ask_parser.set_defaults(func=cmd_ask)

    status_parser = sub.add_parser("status", help="查看当前记忆系统状态")
    status_parser.set_defaults(func=cmd_status)

    find_sessions_parser = sub.add_parser("find-sessions", help="按关键字查找 Codex 会话")
    find_sessions_parser.add_argument("--keyword", default="")
    find_sessions_parser.add_argument("--limit", type=int, default=10)
    find_sessions_parser.set_defaults(func=cmd_find_sessions)

    review_parser = sub.add_parser("review", help="查看最需要回顾或瘦身的记忆")
    review_parser.add_argument("--limit", type=int, default=10)
    review_parser.set_defaults(func=cmd_review)

    cleanup_parser = sub.add_parser("cleanup", help="执行一次瘦身整理")
    cleanup_parser.set_defaults(func=cmd_cleanup)

    integrity_parser = sub.add_parser("integrity", help="检查受保护记忆完整性")
    integrity_parser.set_defaults(func=cmd_integrity)

    benchmark_parser = sub.add_parser("benchmark", help="运行基准回归")
    benchmark_parser.set_defaults(func=cmd_benchmark)

    scan_openclaw_parser = sub.add_parser("scan-openclaw", help="扫描 openclaw 根目录并登记项目")
    scan_openclaw_parser.add_argument("--openclaw-root", default=None)
    scan_openclaw_parser.add_argument("--sync", action="store_true")
    scan_openclaw_parser.set_defaults(func=cmd_scan_openclaw)

    report_openclaw_parser = sub.add_parser("report-openclaw", help="生成 openclaw 观察报告")
    report_openclaw_parser.add_argument("--openclaw-root", default=None)
    report_openclaw_parser.set_defaults(func=cmd_report_openclaw)

    validate_openclaw_parser = sub.add_parser("validate-openclaw", help="运行 openclaw 真实项目验证")
    validate_openclaw_parser.set_defaults(func=cmd_validate_openclaw)

    replay_openclaw_history_parser = sub.add_parser("replay-openclaw-history", help="按 openclaw 对话历史回放并统计记忆命中率")
    replay_openclaw_history_parser.set_defaults(func=cmd_replay_openclaw_history)

    dashboard_parser = sub.add_parser("dashboard", help="生成统一 Memory 指标看板")
    dashboard_parser.set_defaults(func=cmd_dashboard)

    observe_openclaw_parser = sub.add_parser("observe-openclaw", help="一条命令完成 openclaw 扫描、验证、报告和看板")
    observe_openclaw_parser.add_argument("--openclaw-root", default=None)
    observe_openclaw_parser.set_defaults(func=cmd_observe_openclaw)

    watch_openclaw_parser = sub.add_parser("watch-openclaw", help="轮询监听 openclaw 新项目")
    watch_openclaw_parser.add_argument("--openclaw-root", default=None)
    watch_openclaw_parser.add_argument("--interval", type=int, default=10)
    watch_openclaw_parser.set_defaults(func=cmd_watch_openclaw)

    start_watch_openclaw_parser = sub.add_parser("start-watch-openclaw", help="后台启动 openclaw 监听")
    start_watch_openclaw_parser.add_argument("--interval", type=int, default=10)
    start_watch_openclaw_parser.set_defaults(func=cmd_start_watch_openclaw)

    stop_watch_openclaw_parser = sub.add_parser("stop-watch-openclaw", help="停止后台 openclaw 监听")
    stop_watch_openclaw_parser.set_defaults(func=cmd_stop_watch_openclaw)

    watch_status_parser = sub.add_parser("watch-status", help="查看后台 openclaw 监听状态")
    watch_status_parser.set_defaults(func=cmd_watch_status)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
