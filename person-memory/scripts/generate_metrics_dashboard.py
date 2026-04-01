from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "memory_metrics_dashboard.md"
TRACE_PATH = ROOT / "data" / "runtime_data" / "memory" / "logs" / "decision_trace.jsonl"


def run_json(*args: str) -> dict:
    proc = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


def progress_bar(score: float, width: int = 20) -> str:
    score = max(0.0, min(1.0, score))
    filled = round(score * width)
    return "█" * filled + "░" * (width - filled)


def load_recent_traces(limit: int = 8) -> list[dict]:
    if not TRACE_PATH.exists():
        return []
    lines = [line for line in TRACE_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    traces = [json.loads(line) for line in lines[-limit:]]
    return traces


def extract_step(trace: dict, step_name: str) -> dict | None:
    for step in trace.get("policy_steps", []):
        if step.get("step_name") == step_name:
            return step
    return None


def compute_trace_metrics(traces: list[dict]) -> dict:
    if not traces:
        return {
            "trace_count": 0,
            "memory_used_rate": 0.0,
            "avg_used_memory_count": 0.0,
            "entry_read_rate": 0.0,
            "explicit_project_queries": 0,
            "project_query_count": 0,
            "top_reason_codes": [],
        }
    memory_used = 0
    used_memory_total = 0
    entry_read = 0
    project_query_count = 0
    explicit_project_queries = 0
    reason_counter: Counter[str] = Counter()

    for trace in traces:
        final_outcome = trace.get("final_outcome", {})
        if final_outcome.get("memory_used"):
            memory_used += 1
        delivery_step = extract_step(trace, "delivery") or {}
        used_ids = delivery_step.get("payload", {}).get("used_memory_ids", [])
        used_memory_total += len(used_ids)
        entry_step = extract_step(trace, "entry_read") or {}
        if entry_step.get("decision") == "read":
            entry_read += 1
        state = trace.get("state_snapshot", {})
        if str(state.get("scope", "")).startswith("project:"):
            project_query_count += 1
            if state.get("explicit_recall_requested"):
                explicit_project_queries += 1
        for step in trace.get("policy_steps", []):
            for reason in step.get("reason_codes", []):
                reason_counter[reason] += 1

    trace_count = len(traces)
    return {
        "trace_count": trace_count,
        "memory_used_rate": round(memory_used / trace_count, 3),
        "avg_used_memory_count": round(used_memory_total / trace_count, 3),
        "entry_read_rate": round(entry_read / trace_count, 3),
        "explicit_project_queries": explicit_project_queries,
        "project_query_count": project_query_count,
        "top_reason_codes": reason_counter.most_common(10),
    }


def acceptance_scorecard(benchmark: dict, validate_openclaw: dict, integrity: dict, trace_metrics: dict) -> dict[str, float]:
    total = benchmark.get("total", 0) or 1
    used_results = [result for result in benchmark.get("results", []) if result.get("used_memory_ids")]
    must_include_checks = []
    not_contains_checks = []
    delivery_checks = []
    for result in benchmark.get("results", []):
        for check in result.get("checks", []):
            if check["name"] == "must_include_memory_ids":
                must_include_checks.append(check["passed"])
            elif check["name"] == "response_not_contains":
                not_contains_checks.append(check["passed"])
            elif check["name"] == "delivery_level":
                delivery_checks.append(check["passed"])
    retrieval_accuracy = sum(must_include_checks) / len(must_include_checks) if must_include_checks else 1.0
    pollution_control = sum(not_contains_checks) / len(not_contains_checks) if not_contains_checks else 1.0
    delivery_control = sum(delivery_checks) / len(delivery_checks) if delivery_checks else 1.0
    project_hit = validate_openclaw.get("overall_metrics", {}).get("project_hit_rate", 0.0)
    project_isolation = validate_openclaw.get("overall_metrics", {}).get("pollution_free_rate", 0.0)
    stability = 1.0 if integrity.get("status") == "pass" else 0.0
    memory_engagement = trace_metrics["memory_used_rate"]
    overall = (
        benchmark["pass_rate"] * 0.25
        + retrieval_accuracy * 0.20
        + pollution_control * 0.15
        + delivery_control * 0.10
        + project_hit * 0.10
        + project_isolation * 0.10
        + stability * 0.05
        + min(memory_engagement / 0.85, 1.0) * 0.05
    )
    return {
        "总回归通过率": benchmark["pass_rate"],
        "关键记忆命中率": retrieval_accuracy,
        "污染抑制率": pollution_control,
        "交付匹配率": delivery_control,
        "openclaw项目命中率": project_hit,
        "openclaw项目隔离率": project_isolation,
        "保护层稳定性": stability,
        "记忆参与度": memory_engagement,
        "综合评分": round(overall, 3),
    }


def main() -> None:
    benchmark = run_json("scripts/memory_cli.py", "benchmark")
    integrity = run_json("scripts/memory_cli.py", "integrity")
    status = run_json("scripts/memory_cli.py", "status")
    validate_openclaw = run_json("scripts/memory_cli.py", "validate-openclaw")
    openclaw_history = run_json("scripts/memory_cli.py", "replay-openclaw-history")
    traces = load_recent_traces()
    trace_metrics = compute_trace_metrics(traces)
    scorecard = acceptance_scorecard(benchmark, validate_openclaw, integrity, trace_metrics)

    lines: list[str] = []
    lines.append("# Memory 指标看板")
    lines.append("")
    lines.append("## 1. 一眼结论")
    lines.append("")
    lines.append(f"- 基准回归：`{benchmark['passed']}/{benchmark['total']}`，通过率 ` {benchmark['pass_rate']:.3f} `")
    lines.append(f"- openclaw 真实项目验证：`{validate_openclaw['overall_metrics']['passed_cases']}/{validate_openclaw['overall_metrics']['total_cases']}`，通过率 ` {validate_openclaw['overall_metrics']['pass_rate']:.3f} `")
    lines.append(f"- 当前活跃记忆数：`{status['memory_counts']['total']}`")
    lines.append(f"- 当前 trace 数：`{trace_metrics['trace_count']}`")
    lines.append(f"- 综合评分：`{scorecard['综合评分'] * 100:.1f} / 100`")
    lines.append("")
    lines.append("## 2. 核心评分卡")
    lines.append("")
    lines.append("| 指标 | 分数 | 可视化 | 说明 |")
    lines.append("|---|---:|---|---|")
    descriptions = {
        "总回归通过率": "24 个标准回归是否稳定通过",
        "关键记忆命中率": "该命中的 memory_id 是否命中",
        "污染抑制率": "不该出现的内容是否被压制",
        "交付匹配率": "输出粒度是否落在预期层级",
        "openclaw项目命中率": "真实项目问题是否命中当前项目记忆",
        "openclaw项目隔离率": "真实项目问题是否避免串到别的项目",
        "保护层稳定性": "绝密/受保护记忆是否完整",
        "记忆参与度": "真正需要时 memory 是否参与，而不是完全闲置",
        "综合评分": "综合当前版本整体可用性",
    }
    for name, value in scorecard.items():
        lines.append(f"| {name} | {value * 100:.1f} | {progress_bar(value)} | {descriptions[name]} |")
    lines.append("")
    lines.append("## 3. 当前具体数据")
    lines.append("")
    lines.append("### 3.1 Benchmark")
    lines.append("")
    lines.append(f"- 总用例数：`{benchmark['total']}`")
    lines.append(f"- 通过数：`{benchmark['passed']}`")
    lines.append(f"- 通过率：`{benchmark['pass_rate']:.3f}`")
    lines.append("")
    lines.append("### 3.2 openclaw 真实项目")
    lines.append("")
    overall = validate_openclaw["overall_metrics"]
    lines.append(f"- 项目数：`{overall['project_count']}`")
    lines.append(f"- 项目级验证用例数：`{overall['total_cases']}`")
    lines.append(f"- 项目命中率：`{overall['project_hit_rate']:.3f}`")
    lines.append(f"- 污染抑制率：`{overall['pollution_free_rate']:.3f}`")
    lines.append(f"- 交付匹配率：`{overall['delivery_fit_rate']:.3f}`")
    lines.append(f"- 平均同 scope 精度：`{overall['avg_scope_precision']:.3f}`")
    lines.append(f"- 平均单次使用记忆数：`{overall['avg_used_memory_count']:.3f}`")
    lines.append("")
    lines.append("### 3.3 openclaw 对话历史回放")
    lines.append("")
    history_metrics = openclaw_history["metrics"]
    lines.append(f"- 会话数：`{history_metrics['session_count']}`")
    lines.append(f"- 总用户轮次：`{history_metrics['total_turns']}`")
    lines.append(f"- 需要记忆的轮次：`{history_metrics['memory_needed_turns']}`")
    lines.append(f"- 历史回放命中率：`{history_metrics['memory_hit_rate']:.3f}`")
    lines.append(f"- 历史回放记忆使用率：`{history_metrics['memory_used_rate']:.3f}`")
    lines.append(f"- 历史回放同 scope 命中率：`{history_metrics['same_scope_hit_rate']:.3f}`")
    lines.append(f"- 历史回放平均使用记忆数：`{history_metrics['avg_used_memory_count']:.3f}`")
    lines.append("")
    lines.append("### 3.4 当前运行态")
    lines.append("")
    lines.append(f"- 默认项目：`{status['default_project_id']}`")
    lines.append(f"- 活跃记忆总数：`{status['memory_counts']['total']}`")
    lines.append(f"- 最近 trace 数：`{trace_metrics['trace_count']}`")
    lines.append(f"- 记忆使用率：`{trace_metrics['memory_used_rate']:.3f}`")
    lines.append(f"- 平均每轮使用记忆数：`{trace_metrics['avg_used_memory_count']:.3f}`")
    lines.append(f"- 入口文档读取率：`{trace_metrics['entry_read_rate']:.3f}`")
    lines.append("")
    lines.append("## 4. 记忆分布")
    lines.append("")
    lines.append("### 4.1 按层级")
    lines.append("")
    for key, value in status["memory_counts"]["by_layer"].items():
        ratio = value / status["memory_counts"]["total"] if status["memory_counts"]["total"] else 0.0
        lines.append(f"- `{key}`: `{value}`  {progress_bar(ratio, 12)}")
    lines.append("")
    lines.append("### 4.2 按作用域")
    lines.append("")
    for key, value in status["memory_counts"]["by_scope"].items():
        ratio = value / status["memory_counts"]["total"] if status["memory_counts"]["total"] else 0.0
        lines.append(f"- `{key}`: `{value}`  {progress_bar(ratio, 12)}")
    lines.append("")
    lines.append("## 5. 最近日志命中情况")
    lines.append("")
    if not traces:
        lines.append("- 当前还没有 trace。")
    else:
        lines.append("| 查询 | 项目 | query_type | delivery | 命中记忆 | 入口读取 | scope |")
        lines.append("|---|---|---|---:|---|---|---|")
        for trace in traces:
            state = trace.get("state_snapshot", {})
            delivery_step = extract_step(trace, "delivery") or {}
            entry_step = extract_step(trace, "entry_read") or {}
            scope_step = extract_step(trace, "scope_gate") or {}
            used_ids = delivery_step.get("payload", {}).get("used_memory_ids", [])
            query = str(state.get("query", ""))[:28].replace("|", " ")
            lines.append(
                f"| {query} | {trace.get('project_id') or '-'} | {trace.get('query_type')} | "
                f"{trace.get('final_outcome', {}).get('delivery_level', 0)} | "
                f"{', '.join(used_ids) if used_ids else '-'} | "
                f"{entry_step.get('decision', '-')} | "
                f"{scope_step.get('decision', '-')} |"
            )
    lines.append("")
    lines.append("## 5.1 openclaw 历史回放命中情况")
    lines.append("")
    history_results = openclaw_history.get("results", [])
    if not history_results:
        lines.append("- 当前还没有检测到 `openclaw` 下的真实 Codex 会话。")
    else:
        lines.append("| session_id | query_type | need_memory | memory_used | delivery | used_memory_ids | query |")
        lines.append("|---|---|---|---|---:|---|---|")
        for item in history_results[-12:]:
            lines.append(
                f"| {item['session_id']} | {item['query_type']} | "
                f"{'Y' if item['memory_needed'] else 'N'} | {'Y' if item['memory_used'] else 'N'} | "
                f"{item['delivery_level']} | "
                f"{', '.join(item['used_memory_ids']) if item['used_memory_ids'] else '-'} | "
                f"{item['query'][:44].replace('|', ' ')} |"
            )
    lines.append("")
    lines.append("## 6. 主要触发原因码")
    lines.append("")
    if trace_metrics["top_reason_codes"]:
        lines.append("| reason_code | 次数 |")
        lines.append("|---|---:|")
        for code, count in trace_metrics["top_reason_codes"]:
            lines.append(f"| {code} | {count} |")
    else:
        lines.append("- 暂无数据。")
    lines.append("")
    lines.append("## 7. 怎么读这个面板")
    lines.append("")
    lines.append("- 如果 `openclaw项目命中率` 低，说明新项目虽然导进来了，但项目问题没优先命中项目记忆。")
    lines.append("- 如果 `历史回放命中率` 低，说明真实多轮对话里该调记忆的时候没有调起来。")
    lines.append("- 如果 `openclaw项目隔离率` 低，说明串项目了。")
    lines.append("- 如果 `关键记忆命中率` 低，但 `总回归通过率` 还高，通常是排序偏差，不是整体崩坏。")
    lines.append("- 如果 `平均单次使用记忆数` 持续升高，说明输出越来越重，需要继续收紧前台候选。")
    lines.append("- 最近日志命中表就是你说的“去看项目日志有没有取到对应记忆并返回”。这里直接看 `命中记忆` 列。")
    lines.append("")
    lines.append("## 8. 最省事的真实项目验证方式")
    lines.append("")
    lines.append("你以后不需要自己拼多个命令，只要两条：")
    lines.append("")
    lines.append("```powershell")
    lines.append("python scripts/memory_cli.py observe-openclaw")
    lines.append("python scripts/memory_cli.py dashboard")
    lines.append("```")
    lines.append("")
    lines.append("- `observe-openclaw`：扫描 openclaw、新项目导入、真实项目验证、对话历史回放、生成项目观察报告")
    lines.append("- `dashboard`：生成统一可视化指标面板")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": "ok", "report_path": str(REPORT_PATH)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
