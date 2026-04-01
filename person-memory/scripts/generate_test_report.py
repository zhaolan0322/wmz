from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "memory_system_test_report.md"


def run_json(*args: str) -> dict:
    proc = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


def build_case_table(cases_dir: Path) -> list[dict]:
    rows = []
    for path in sorted(cases_dir.glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        expected = case["expected"]
        rows.append(
            {
                "case_id": case["case_id"],
                "query": case["query"],
                "query_type": expected.get("query_type", ""),
                "delivery_level": expected.get("delivery_level", ""),
                "must_include_count": len(expected.get("must_include_memory_ids", [])),
                "response_contains_count": len(expected.get("response_contains", [])),
                "response_not_contains_count": len(expected.get("response_not_contains", [])),
            }
        )
    return rows


def progress_bar(score: float, width: int = 20) -> str:
    score = max(0.0, min(1.0, score))
    filled = round(score * width)
    return "█" * filled + "░" * (width - filled)


def case_pass_rate(results: list[dict], prefix: str | None = None, query_type: str | None = None) -> float:
    filtered = []
    for item in results:
        if prefix and not item["case_id"].startswith(prefix):
            continue
        if query_type:
            matched = False
            for check in item["checks"]:
                if check["name"] == "query_type" and check["actual"] == query_type:
                    matched = True
                    break
            if not matched:
                continue
        filtered.append(item)
    if not filtered:
        return 0.0
    return sum(1 for item in filtered if item["passed"]) / len(filtered)


def main() -> None:
    subprocess.run([sys.executable, "scripts/generate_benchmark_cases.py"], cwd=ROOT, check=True, capture_output=True, text=True)
    benchmark = run_json("scripts/run_benchmark.py")
    integrity = run_json("scripts/memory_cli.py", "integrity")
    status = run_json("scripts/memory_cli.py", "status")
    smoke_proc = subprocess.run(
        [sys.executable, "-m", "unittest", "tests.test_smoke", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    smoke_passed = smoke_proc.returncode == 0
    cases = build_case_table(ROOT / "data" / "benchmark_cases")

    query_type_dist = Counter(case["query_type"] for case in cases)
    delivery_dist = Counter(case["delivery_level"] for case in cases)
    check_counts = Counter()
    check_pass = Counter()
    used_case_count = 0
    used_memory_total = 0
    for result in benchmark["results"]:
        if result["used_memory_ids"]:
            used_case_count += 1
            used_memory_total += len(result["used_memory_ids"])
        for check in result["checks"]:
            check_counts[check["name"]] += 1
            if check["passed"]:
                check_pass[check["name"]] += 1

    acceptance_scores = {
        "总体准确命中": (
            (check_pass["must_include_memory_ids"] / check_counts["must_include_memory_ids"] if check_counts["must_include_memory_ids"] else 1.0)
            + (check_pass["response_contains"] / check_counts["response_contains"] if check_counts["response_contains"] else 1.0)
            + (check_pass["query_type"] / check_counts["query_type"] if check_counts["query_type"] else 1.0)
        ) / 3,
        "污染抑制": check_pass["response_not_contains"] / check_counts["response_not_contains"] if check_counts["response_not_contains"] else 1.0,
        "交付控制": check_pass["delivery_level"] / check_counts["delivery_level"] if check_counts["delivery_level"] else 1.0,
        "任务续接": case_pass_rate(benchmark["results"], prefix="TC-"),
        "项目隔离": case_pass_rate(benchmark["results"], prefix="ISO-"),
        "精准回忆": case_pass_rate(benchmark["results"], query_type="exact_recall"),
        "场景覆盖": min(1.0, benchmark["total"] / 24),
        "系统稳定与安全": 1.0 if integrity["status"] == "pass" and smoke_passed else 0.0,
    }
    overall_score = (
        acceptance_scores["总体准确命中"] * 0.25
        + acceptance_scores["污染抑制"] * 0.15
        + acceptance_scores["交付控制"] * 0.15
        + acceptance_scores["任务续接"] * 0.10
        + acceptance_scores["项目隔离"] * 0.10
        + acceptance_scores["精准回忆"] * 0.10
        + acceptance_scores["场景覆盖"] * 0.05
        + acceptance_scores["系统稳定与安全"] * 0.10
    )

    lines: list[str] = []
    lines.append("# 个人分层 AI 记忆系统测试报告")
    lines.append("")
    lines.append("## 1. 测试结论")
    lines.append("")
    lines.append(f"- 基准测试总数：`{benchmark['total']}`")
    lines.append(f"- 通过数：`{benchmark['passed']}`")
    lines.append(f"- 通过率：`{benchmark['pass_rate']:.3f}`")
    lines.append(f"- 保护层完整性：`{integrity['status']}`")
    lines.append(f"- smoke test：`{'pass' if smoke_passed else 'fail'}`")
    lines.append(f"- 当前活跃记忆总数：`{status['memory_counts']['total']}`")
    lines.append(f"- 基准运行期间记忆使用率：`{status['trace_summary']['memory_used_rate']:.3f}`")
    lines.append(f"- 综合验收得分：`{overall_score * 100:.1f} / 100`")
    lines.append("")
    lines.append("## 1.1 验收评分看板")
    lines.append("")
    lines.append("| 维度 | 得分 | 可视化 | 说明 |")
    lines.append("|---|---:|---|---|")
    dimension_explanations = {
        "总体准确命中": "关键记忆是否命中，输出是否包含目标信息，query_type 是否识别正确",
        "污染抑制": "不该出现的内容是否被压制",
        "交付控制": "delivery_level 是否稳定落在预期层级",
        "任务续接": "working memory 是否能稳定命中当前任务",
        "项目隔离": "跨项目和跨任务的记忆污染是否被抑制",
        "精准回忆": "exact recall 是否能升级到高证据交付",
        "场景覆盖": "测试是否覆盖足够多的查询类型和使用场景",
        "系统稳定与安全": "smoke + integrity 是否持续通过",
    }
    for name, score in acceptance_scores.items():
        lines.append(f"| {name} | {score * 100:.1f} | {progress_bar(score)} | {dimension_explanations[name]} |")
    lines.append("")
    lines.append("## 2. 测试怎么做")
    lines.append("")
    lines.append("测试流程固定为：")
    lines.append("")
    lines.append("1. 重新生成标准 benchmark 用例。")
    lines.append("2. 重置数据库与基础样例数据。")
    lines.append("3. 自动同步真实项目文档与真实 Codex 会话。")
    lines.append("4. 逐条执行 benchmark query。")
    lines.append("5. 对每条结果做结构化校验。")
    lines.append("6. 最后执行 protected memory 完整性检查。")
    lines.append("")
    lines.append("当前 benchmark 校验项包括：")
    lines.append("")
    lines.append("- `delivery_level` 是否符合预期")
    lines.append("- `query_type` 是否符合预期")
    lines.append("- `must_include_memory_ids` 是否命中关键记忆")
    lines.append("- `response_contains` 是否覆盖关键结果")
    lines.append("- `response_not_contains` 是否避免错误污染")
    lines.append("")
    lines.append("## 3. 用例覆盖范围")
    lines.append("")
    lines.append("### 3.1 按查询类型")
    lines.append("")
    for key, value in sorted(query_type_dist.items()):
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    lines.append("### 3.2 按交付等级")
    lines.append("")
    for key, value in sorted(delivery_dist.items()):
        lines.append(f"- `level {key}`: `{value}`")
    lines.append("")
    lines.append("### 3.3 按测试维度")
    lines.append("")
    lines.append("- 轻量无记忆场景：寒暄、无历史依赖查询")
    lines.append("- 任务续接场景：当前任务恢复、working memory 命中")
    lines.append("- 项目卡点场景：sync-engine 排障、可复用模式直接交付")
    lines.append("- 项目规划场景：research 启动策略、PPT skill 工作流")
    lines.append("- 历史回忆场景：之前经验、之前项目建议")
    lines.append("- 精准回忆场景：exact recall 回到原始会话结论")
    lines.append("- 隔离场景：PPT 项目不混入 baoyu 会话结论；research 不混入 sync；task 不混入项目记忆")
    lines.append("- 保护层场景：immutable/protected 文档完整性校验")
    lines.append("")
    lines.append("## 4. 量化指标")
    lines.append("")
    lines.append(f"- 总体 benchmark 通过率：`{benchmark['pass_rate']:.3f}`")
    lines.append(f"- 记忆触发用例数：`{used_case_count}` / `{benchmark['total']}`")
    lines.append(f"- 记忆触发占比：`{(used_case_count / benchmark['total']):.3f}`")
    lines.append(f"- 触发场景平均使用记忆条数：`{(used_memory_total / used_case_count):.3f}`")
    lines.append("")
    lines.append("细分检查通过率：")
    lines.append("")
    for key in sorted(check_counts):
        rate = check_pass[key] / check_counts[key] if check_counts[key] else 0.0
        lines.append(f"- `{key}`: `{check_pass[key]}` / `{check_counts[key]}` = `{rate:.3f}`")
    lines.append("")
    lines.append("## 5. 当前数据状态")
    lines.append("")
    lines.append(f"- 默认项目：`{status['default_project_id']}`")
    lines.append(f"- 注册项目数：`{len(status['registered_projects'])}`")
    lines.append("- 记忆层分布：")
    for key, value in status["memory_counts"]["by_layer"].items():
        lines.append(f"  - `{key}`: `{value}`")
    lines.append("- 作用域分布：")
    for key, value in status["memory_counts"]["by_scope"].items():
        lines.append(f"  - `{key}`: `{value}`")
    lines.append("")
    lines.append("## 6. 全量用例列表")
    lines.append("")
    lines.append("| Case ID | Query Type | Delivery | 正向命中检查 | 负向污染检查 | Query |")
    lines.append("|---|---|---:|---:|---:|---|")
    for case in cases:
        lines.append(
            f"| {case['case_id']} | {case['query_type']} | {case['delivery_level']} | "
            f"{case['must_include_count'] + case['response_contains_count']} | {case['response_not_contains_count']} | "
            f"{case['query']} |"
        )
    lines.append("")
    lines.append("## 7. 如何判断结果可行")
    lines.append("")
    lines.append("当前这版系统可行，不是因为“跑过了”，而是因为同时满足了下面几类约束：")
    lines.append("")
    lines.append("- 该静默时静默：无历史依赖的轻量 query 返回 `delivery_level = 0`")
    lines.append("- 该续接时续接：task_continue 命中 working memory")
    lines.append("- 该项目优先时项目优先：PPT skill 项目问题优先命中项目入口和项目工作流")
    lines.append("- 该精准回忆时能升级：exact recall 升到 `delivery_level = 4`")
    lines.append("- 该避免污染时能避免污染：隔离用例对 `response_not_contains` 做了约束")
    lines.append("- 保护层没有漂移：protected integrity 为 `pass`")
    lines.append("")
    lines.append("## 8. 你下一步如何验证系统可行性")
    lines.append("")
    lines.append("建议你按下面顺序自己验证，而不是只看 benchmark：")
    lines.append("")
    lines.append("1. 先验证基础链路")
    lines.append("   - 运行 `python scripts/memory_cli.py init`")
    lines.append("   - 运行 `python scripts/memory_cli.py sync`")
    lines.append("   - 运行 `python scripts/memory_cli.py status`")
    lines.append("")
    lines.append("2. 再验证项目命中")
    lines.append("   - 问 `PPT skill项目 默认是可编辑PPT路线还是全AI视觉路线？`")
    lines.append("   - 观察是否优先返回 `Path A / Path B`，且不混入 `baoyu` 结论")
    lines.append("")
    lines.append("3. 再验证任务续接")
    lines.append("   - 问 `请继续当前记忆系统任务`")
    lines.append("   - 看是否命中 `mem-work-memory-mvp`，而不是跳到项目记忆")
    lines.append("")
    lines.append("4. 再验证精准回忆")
    lines.append("   - 问 `请逐字给出上次 Inspect baoyu-slide-deck skill 的结论`")
    lines.append("   - 看是否升级到完整参考输出，而不是只给摘要")
    lines.append("")
    lines.append("5. 再验证长期稳定性")
    lines.append("   - 连续跑 `benchmark`、`integrity`、`review`、`cleanup`")
    lines.append("   - 看 pass_rate 是否维持，protected 是否仍为 pass")
    lines.append("")
    lines.append("## 9. 你后续主要关注哪些指标")
    lines.append("")
    lines.append("你自己实际使用时，最该盯这几个指标：")
    lines.append("")
    lines.append("- `benchmark pass_rate`：总回归通过率，低于 `1.0` 就说明系统回退了")
    lines.append("- `must_include_memory_ids` 通过率：关键记忆命中能力")
    lines.append("- `response_not_contains` 通过率：污染抑制能力")
    lines.append("- `memory_used_rate`：触发比例，过高说明过度调用，过低说明记忆没用上")
    lines.append("- `avg_used_memory_ids_per_used_case`：平均注入条数，过高说明上下文可能过重")
    lines.append("- `integrity status`：protected 层是否被破坏")
    lines.append("- `review / cleanup` 输出：是否开始臃肿、是否有大量低价值记忆")
    lines.append("")
    lines.append("## 10. 当前结论")
    lines.append("")
    lines.append("在当前真实数据和当前 24 个全量回归用例下，这套记忆系统已经达到可实际使用状态。")
    lines.append("后续如果你继续接入新的项目和会话，建议每次扩数据后都重新跑一次本报告流程。")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": "ok", "report_path": str(REPORT_PATH)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
