from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = ROOT / "data" / "benchmark_cases"


CASES = [
    {
        "filename": "01_chat_greeting.json",
        "case_id": "CH-001",
        "query": "你好",
        "environment": {},
        "expected": {
            "query_type": "chat_simple",
            "delivery_level": 0,
            "response_contains": ["无需显式调用历史记忆"],
        },
    },
    {
        "filename": "02_chat_weather.json",
        "case_id": "CH-002",
        "query": "今天天气怎么样",
        "environment": {},
        "expected": {
            "query_type": "chat_simple",
            "delivery_level": 0,
            "response_contains": ["无需显式调用历史记忆"],
        },
    },
    {
        "filename": "03_task_continue_memory_system.json",
        "case_id": "TC-001",
        "query": "请继续当前记忆系统任务",
        "environment": {"task_id": "task-memory-mvp"},
        "expected": {
            "query_type": "task_continue",
            "delivery_level": 2,
            "must_include_memory_ids": ["mem-work-memory-mvp"],
            "response_contains": ["设计稿", "MVP"],
        },
    },
    {
        "filename": "04_task_continue_memory_system_variant.json",
        "case_id": "TC-002",
        "query": "继续现在的论文记忆系统工作",
        "environment": {"task_id": "task-memory-mvp"},
        "expected": {
            "query_type": "task_continue",
            "delivery_level": 2,
            "must_include_memory_ids": ["mem-work-memory-mvp"],
            "response_contains": ["MVP"],
        },
    },
    {
        "filename": "05_problem_blocked_sync_primary.json",
        "case_id": "PB-001",
        "query": "这个 sync pipeline 的问题和之前很像，我现在卡住了，先该检查什么？",
        "environment": {"project_id": "sync-engine", "task_id": "task-sync-1", "delivery_level_ceiling": 3},
        "expected": {
            "query_type": "problem_blocked",
            "delivery_level": 3,
            "must_include_memory_ids": ["mem-proc-sync-debug"],
            "response_contains": ["缩范围", "幂等更新", "缓存"],
        },
    },
    {
        "filename": "06_problem_blocked_sync_variant.json",
        "case_id": "PB-002",
        "query": "sync-engine 现在卡住了，优先排查哪些点？",
        "environment": {"project_id": "sync-engine", "task_id": "task-sync-2", "delivery_level_ceiling": 3},
        "expected": {
            "query_type": "problem_blocked",
            "delivery_level": 3,
            "must_include_memory_ids": ["mem-proc-sync-debug"],
            "response_contains": ["幂等更新", "缓存"],
        },
    },
    {
        "filename": "07_historical_sync_method.json",
        "case_id": "HL-001",
        "query": "之前 sync-engine 是怎么排查同步问题的？",
        "environment": {"project_id": "sync-engine", "explicit_recall_requested": True, "delivery_level_ceiling": 3},
        "expected": {
            "query_type": "problem_blocked",
            "delivery_level": 3,
            "must_include_memory_ids": ["mem-proc-sync-debug"],
            "response_contains": ["三步排查", "幂等更新"],
        },
    },
    {
        "filename": "08_project_planning_sync_flow.json",
        "case_id": "PP-001",
        "query": "sync-engine 的排查流程怎么走？",
        "environment": {"project_id": "sync-engine", "explicit_recall_requested": True, "delivery_level_ceiling": 3},
        "expected": {
            "query_type": "problem_blocked",
            "delivery_level": 3,
            "must_include_memory_ids": ["mem-proc-sync-debug"],
            "response_contains": ["缩范围", "回写"],
        },
    },
    {
        "filename": "09_project_planning_research_start.json",
        "case_id": "PP-002",
        "query": "我准备开始一个新的研究任务，怎么起步更高效？",
        "environment": {"project_id": "research", "task_id": "task-research-1", "delivery_level_ceiling": 2},
        "expected": {
            "query_type": "project_planning",
            "delivery_level": 2,
            "must_include_memory_ids": ["mem-dyn-research-start"],
            "response_contains": ["先定输出格式", "再补资料"],
        },
    },
    {
        "filename": "10_problem_blocked_research.json",
        "case_id": "PB-003",
        "query": "研究任务卡住了，先看什么",
        "environment": {"project_id": "research", "task_id": "task-research-2", "delivery_level_ceiling": 2},
        "expected": {
            "query_type": "problem_blocked",
            "delivery_level": 2,
            "must_include_memory_ids": ["mem-dyn-research-start"],
            "response_contains": ["先定输出格式", "目标边界"],
        },
    },
    {
        "filename": "11_historical_research_start.json",
        "case_id": "HL-002",
        "query": "上次研究任务是怎么起步的？",
        "environment": {"project_id": "research", "explicit_recall_requested": True, "delivery_level_ceiling": 2},
        "expected": {
            "query_type": "project_planning",
            "delivery_level": 2,
            "must_include_memory_ids": ["mem-dyn-research-start"],
            "response_contains": ["先定输出格式", "再补资料"],
        },
    },
    {
        "filename": "12_project_planning_research_variant.json",
        "case_id": "PP-003",
        "query": "research 项目一般怎么开始？",
        "environment": {"project_id": "research", "explicit_recall_requested": True, "delivery_level_ceiling": 2},
        "expected": {
            "query_type": "project_planning",
            "delivery_level": 2,
            "must_include_memory_ids": ["mem-dyn-research-start"],
            "response_contains": ["先定输出格式", "再补资料"],
        },
    },
    {
        "filename": "13_ppt_route_choice.json",
        "case_id": "PP-004",
        "query": "PPT skill项目 默认是可编辑PPT路线还是全AI视觉路线？",
        "environment": {"project_id": "ppt-skill-project", "task_id": "task-ppt-1", "explicit_recall_requested": True, "delivery_level_ceiling": 2},
        "expected": {
            "query_type": "project_planning",
            "delivery_level": 2,
            "must_include_memory_ids": ["mem-project-workflow-ecaf7572f216", "mem-project-entry-2e4187047d72"],
            "response_contains": ["Path A", "Path B", "可编辑 HTML", "全 AI"],
        },
    },
    {
        "filename": "14_ppt_workflow.json",
        "case_id": "PP-005",
        "query": "PPT skill项目 的工作流怎么走？",
        "environment": {"project_id": "ppt-skill-project", "explicit_recall_requested": True, "delivery_level_ceiling": 2},
        "expected": {
            "query_type": "project_planning",
            "delivery_level": 2,
            "must_include_memory_ids": ["mem-project-workflow-ecaf7572f216"],
            "response_contains": ["AI 演示文稿全流程工作流", "Path A", "Path B"],
        },
    },
    {
        "filename": "15_ppt_templates_constraints.json",
        "case_id": "PP-006",
        "query": "PPT skill项目 有哪些模板和导出约束？",
        "environment": {"project_id": "ppt-skill-project", "explicit_recall_requested": True, "delivery_level_ceiling": 2},
        "expected": {
            "query_type": "chat_simple",
            "delivery_level": 2,
            "must_include_memory_ids": ["mem-project-prompt-templates-20e750d7cdd3"],
            "response_contains": ["模板", "html2pptx", "导出稳定"],
        },
    },
    {
        "filename": "16_ppt_historical_advice.json",
        "case_id": "HL-003",
        "query": "根据之前的 PPT skill项目 经验给我建议",
        "environment": {"project_id": "ppt-skill-project", "explicit_recall_requested": True, "delivery_level_ceiling": 2},
        "expected": {
            "query_type": "historical_lookup",
            "delivery_level": 2,
            "must_include_memory_ids": ["mem-project-entry-2e4187047d72", "mem-project-workflow-ecaf7572f216"],
            "response_contains": ["项目记忆优先于全局相似经验"],
        },
    },
    {
        "filename": "17_ppt_course_outline.json",
        "case_id": "PP-007",
        "query": "PPT skill项目 的课程内容结构是什么？",
        "environment": {"project_id": "ppt-skill-project", "explicit_recall_requested": True, "delivery_level_ceiling": 2},
        "expected": {
            "query_type": "chat_simple",
            "delivery_level": 2,
            "must_include_memory_ids": ["mem-project-course-outline-1b1fc7708c62"],
            "response_contains": ["课程内容结构", "Dify 财务工作流实战训练营"],
        },
    },
    {
        "filename": "18_exact_recall_baoyu.json",
        "case_id": "ER-001",
        "query": "请逐字给出上次 Inspect baoyu-slide-deck skill 的结论",
        "environment": {"explicit_recall_requested": True, "delivery_level_ceiling": 4},
        "expected": {
            "query_type": "exact_recall",
            "delivery_level": 4,
            "must_include_memory_ids": ["mem-import-codex-conv-ddcd4c6da27b", "mem-import-codex-learned-dce458fb95f1"],
            "response_contains": ["完整参考记忆如下", "可编辑程度", "每页一张全屏图片"],
        },
    },
    {
        "filename": "19_historical_baoyu_summary.json",
        "case_id": "HL-004",
        "query": "之前那个 baoyu slide deck skill 会话主要结论是什么？",
        "environment": {"explicit_recall_requested": True, "delivery_level_ceiling": 2},
        "expected": {
            "query_type": "historical_lookup",
            "delivery_level": 2,
            "must_include_memory_ids": ["mem-import-codex-learned-dce458fb95f1"],
            "response_contains": ["可编辑程度", "每页一张全屏图片"],
        },
    },
    {
        "filename": "20_ppt_first_look.json",
        "case_id": "PB-004",
        "query": "请根据之前的经验，告诉我做 PPT skill 时先看什么",
        "environment": {"project_id": "ppt-skill-project", "explicit_recall_requested": True, "delivery_level_ceiling": 2},
        "expected": {
            "query_type": "problem_blocked",
            "delivery_level": 2,
            "must_include_memory_ids": ["mem-project-entry-2e4187047d72", "mem-project-workflow-ecaf7572f216"],
            "response_contains": ["先看项目工作流总览", "模板与导出约束"],
        },
    },
    {
        "filename": "21_ppt_isolation_no_baoyu.json",
        "case_id": "ISO-001",
        "query": "PPT skill项目 默认是可编辑PPT路线还是全AI视觉路线？",
        "environment": {"project_id": "ppt-skill-project", "explicit_recall_requested": True, "delivery_level_ceiling": 2},
        "expected": {
            "query_type": "project_planning",
            "delivery_level": 2,
            "must_include_memory_ids": ["mem-project-workflow-ecaf7572f216"],
            "response_contains": ["Path A", "Path B"],
            "response_not_contains": ["每页一张全屏图片", "baoyu"],
        },
    },
    {
        "filename": "22_research_isolation_no_sync.json",
        "case_id": "ISO-002",
        "query": "我准备开始一个新的研究任务，怎么起步更高效？",
        "environment": {"project_id": "research", "task_id": "task-research-1", "delivery_level_ceiling": 2},
        "expected": {
            "query_type": "project_planning",
            "delivery_level": 2,
            "must_include_memory_ids": ["mem-dyn-research-start"],
            "response_contains": ["先定输出格式", "再补资料"],
            "response_not_contains": ["幂等更新", "缓存失效"],
        },
    },
    {
        "filename": "23_sync_isolation_no_research.json",
        "case_id": "ISO-003",
        "query": "sync-engine 现在卡住了，优先排查哪些点？",
        "environment": {"project_id": "sync-engine", "task_id": "task-sync-2", "delivery_level_ceiling": 3},
        "expected": {
            "query_type": "problem_blocked",
            "delivery_level": 3,
            "must_include_memory_ids": ["mem-proc-sync-debug"],
            "response_contains": ["幂等更新", "缓存"],
            "response_not_contains": ["Dify", "课前导入", "输出格式"],
        },
    },
    {
        "filename": "24_task_continue_no_project_pollution.json",
        "case_id": "ISO-004",
        "query": "请继续当前记忆系统任务",
        "environment": {"task_id": "task-memory-mvp"},
        "expected": {
            "query_type": "task_continue",
            "delivery_level": 2,
            "must_include_memory_ids": ["mem-work-memory-mvp"],
            "response_contains": ["MVP"],
            "response_not_contains": ["Path A", "财务工作流", "幂等更新"],
        },
    }
]


def main() -> None:
    CASES_DIR.mkdir(parents=True, exist_ok=True)
    for existing in CASES_DIR.glob("*.json"):
        existing.unlink()
    for case in CASES:
        payload = {
            "case_id": case["case_id"],
            "version": "v1.0",
            "query": case["query"],
            "environment": case["environment"],
            "expected": case["expected"],
        }
        (CASES_DIR / case["filename"]).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    print(json.dumps({"status": "ok", "generated_cases": len(CASES)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
