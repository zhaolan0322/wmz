from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from memory_system_runtime import MemorySystemApp
from memory_system_runtime.core.config import ConfigBundle
from memory_system_runtime.core.models import MemoryItem
from memory_system_runtime.protected.integrity_checker import sha256_file
from memory_system_runtime.storage.archive_store import ArchiveStore
from memory_system_runtime.storage.protected_store import ProtectedStore


def main() -> None:
    app = MemorySystemApp(ROOT)
    app.initialize()
    config = ConfigBundle(ROOT)
    data_root = ROOT / "data" / "runtime_data"
    (data_root / "memory" / "logs").mkdir(parents=True, exist_ok=True)
    (data_root / "memory" / "archive").mkdir(parents=True, exist_ok=True)
    trace_log_path = Path(config.memory["paths"]["trace_log"])
    trace_log_path.parent.mkdir(parents=True, exist_ok=True)
    trace_log_path.write_text("", encoding="utf-8")
    protected_store = ProtectedStore(data_root / "protected", config.memory["protected"]["manifest_file"])
    archive = ArchiveStore(data_root / "memory" / "archive")

    protected_files = {
        "immutable_identity.md": "# Immutable Identity\n\n- canonical_name: personal-memory-system\n- default_language: zh-CN\n",
        "immutable_system_profile.md": "# Immutable System Profile\n\n- safety_mode: strict\n- cleanup_auto_delete_protected: false\n",
        "immutable_policy_anchor.md": "# Immutable Policy Anchor\n\n- policy_version: v0.1.0\n- threshold_version: default\n",
        "entry.md": (
            "# 固定入口\n\n"
            "## 系统身份\n"
            "- 这是个人分层 AI 记忆系统的固定轻量入口。\n"
            "- 默认语言：中文。\n"
            "- 默认输出策略：summary_first。\n\n"
            "## 默认读取顺序\n"
            "1. 当前 task\n"
            "2. 当前 project\n"
            "3. global 稳定记忆\n"
            "4. 必要时再回 raw archive\n\n"
            "## 核心约束\n"
            "- 能不取就不取。\n"
            "- 能不进就不进。\n"
            "- 能少给就不少给。\n"
            "- 默认最小足够交付。\n\n"
            "## 当前主分类规则\n"
            "- 先判作用域：global / project / task / session。\n"
            "- 再判稳定性：immutable / stable / dynamic / temporary。\n"
            "- 再判内容类型：fact / preference / decision / experience / procedure / episode。\n"
            "- 最后判调用方式：silent_use / summary_first / template_ready / exact_recall_required。\n"
        ),
        "classification_rules.md": (
            "# 记忆分类判定规则\n\n"
            "## 一、主归属判定\n"
            "1. 离开当前项目仍然成立，优先归 global。\n"
            "2. 只在某个项目内成立，优先归 project。\n"
            "3. 只服务当前一次任务，优先归 task。\n"
            "4. 仅当前窗口临时有效，优先归 session 或 working。\n\n"
            "## 二、稳定性判定\n"
            "- 长期重复有效：stable。\n"
            "- 几周内有价值但可能变化：dynamic。\n"
            "- 只在当前阶段有效：temporary。\n"
            "- 不允许自动改动：immutable。\n\n"
            "## 三、内容类型判定\n"
            "- 事实：fact\n"
            "- 偏好：preference\n"
            "- 决策：decision\n"
            "- 经验：experience\n"
            "- 流程：procedure\n"
            "- 原始经历：episode\n\n"
            "## 四、调用方式判定\n"
            "- 只需内部吸收：silent_use。\n"
            "- 默认给摘要：summary_first。\n"
            "- 适合直接复用：template_ready。\n"
            "- 必须保留原话和原证据：exact_recall_required。\n\n"
            "## 五、升级规则\n"
            "- 临时 task 记忆连续两次以上复用且仍成立，才考虑升级到 project 或 global。\n"
            "- 项目长期工作流默认放入 project + stable + procedure。\n"
            "- 固定参数、身份、硬约束默认标记 exact_recall_required。\n"
        ),
    }
    file_entries = []
    for name, content in protected_files.items():
        path = protected_store.write_file(name, content)
        file_entries.append({"path": str(path), "sha256": sha256_file(path)})
    protected_store.write_manifest(
        {
            "protected_manifest_version": "1.0",
            "policy_version": "v0.1.0",
            "files": file_entries,
            "created_at": "2026-03-06T14:00:00+08:00",
        }
    )

    archive.write_text(
        "projects/sync-engine/issue_001.txt",
        "上次在 sync pipeline 中遇到的问题是状态漂移。处理方法是先缩小范围，再检查幂等更新，最后验证缓存失效时机。",
    )
    archive.write_text(
        "projects/research/notes_001.txt",
        "研究任务启动时，优先先定输出格式，再补资料，不要先无边界搜集。",
    )

    with app.store.connect() as conn:
        conn.execute("DELETE FROM trace_steps")
        conn.execute("DELETE FROM decision_traces")
        conn.execute("DELETE FROM cleanup_actions")
        conn.execute("DELETE FROM memory_items")
        conn.commit()

    memories = [
        MemoryItem(
            memory_id="mem-core-entry",
            layer="core",
            memory_type="system_entry",
            scope="global",
            title="系统固定入口摘要",
            summary="固定入口用于每次轻量启动时先确认系统身份、默认读取顺序、最小交付原则以及三维分类规则。",
            keywords=["固定入口", "默认读取顺序", "最小交付", "分类规则"],
            source_refs=["protected://entry.md"],
            importance=0.98,
            confidence=0.98,
            strength=1.0,
            auto_inject_level="stable_only",
            delivery_options={
                "keyword_hint": ["固定入口", "默认读取顺序", "最小交付"],
                "method_summary": "先判作用域，再判稳定性，再判类型，默认最小足够交付。",
            },
        ),
        MemoryItem(
            memory_id="mem-core-zh-structured",
            layer="core",
            memory_type="preference",
            scope="global",
            title="中文简洁偏好",
            summary="用户偏好中文输出，且更喜欢简洁但结构化的工程说明。",
            keywords=["中文", "简洁", "结构化"],
            source_refs=["protected://immutable_identity.md"],
            importance=0.95,
            confidence=0.95,
            strength=1.0,
            auto_inject_level="stable_only",
            delivery_options={"keyword_hint": ["中文", "简洁", "结构化"]},
        ),
        MemoryItem(
            memory_id="mem-proc-sync-debug",
            layer="procedural",
            memory_type="procedure",
            scope="project:sync-engine",
            title="同步问题排查模式",
            summary="遇到同步链路问题时，先缩小范围，再检查幂等更新路径，最后验证缓存失效和状态回写时机。",
            keywords=["同步", "幂等更新", "缓存失效", "状态回写"],
            source_refs=["archive://projects/sync-engine/issue_001.txt"],
            importance=0.85,
            confidence=0.88,
            strength=0.9,
            delivery_options={
                "keyword_hint": ["同步", "幂等更新", "缓存失效"],
                "method_summary": "先缩小范围，再检查幂等更新路径，最后验证缓存失效和状态回写时机。",
                "reusable_pattern": "直接沿用三步排查：缩范围 -> 查幂等更新 -> 验证缓存与回写。",
            },
        ),
        MemoryItem(
            memory_id="mem-dyn-research-start",
            layer="dynamic",
            memory_type="experience",
            scope="project:research",
            title="研究任务启动方式",
            summary="当启动研究型任务时，先定义输出格式和目标，再补资料，避免先发散搜集。",
            keywords=["研究", "输出格式", "先定目标"],
            source_refs=["archive://projects/research/notes_001.txt"],
            importance=0.80,
            confidence=0.82,
            strength=0.66,
            delivery_options={
                "keyword_hint": ["输出格式", "目标边界"],
                "method_summary": "先定输出格式和目标边界，再补资料。",
                "reusable_pattern": "沿用研究启动模板：先定输出 -> 再补资料 -> 最后展开细节。",
            },
        ),
        MemoryItem(
            memory_id="mem-work-memory-mvp",
            layer="working",
            memory_type="task_state",
            scope="task:task-memory-mvp",
            title="当前论文任务",
            summary="当前主要任务是把个人分层 AI 记忆系统从设计稿推进到可运行 MVP。",
            keywords=["MVP", "设计稿", "实现"],
            source_refs=["session://current"],
            importance=0.75,
            confidence=0.90,
            strength=0.66,
            delivery_options={"method_summary": "当前重点是把设计稿落成可运行 MVP，而不是继续扩展概念。"},
        ),
    ]
    for memory in memories:
        app.store.upsert_memory(memory)

    print(json.dumps({"status": "ok", "message": "数据库和样例数据已初始化"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
