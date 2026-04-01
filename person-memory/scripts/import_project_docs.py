from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from memory_system_runtime import MemorySystemApp
from memory_system_runtime.core.config import ConfigBundle
from memory_system_runtime.core.models import MemoryItem
from memory_system_runtime.core.utils import normalize_text, tokenize
from memory_system_runtime.storage.archive_store import ArchiveStore


STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "ppt",
    "pptx",
    "slide",
    "slides",
    "skill",
    "html",
    "path",
    "用户",
    "可以",
    "需要",
    "一个",
    "这个",
    "那个",
    "使用",
    "进行",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="导入项目文档为项目级记忆")
    parser.add_argument("--project-id", required=True, help="项目 ID，例如 ppt-skill-project")
    parser.add_argument("--project-name", required=True, help="项目显示名称，例如 PPT skill项目")
    parser.add_argument("--project-path", required=True, help="项目路径")
    return parser.parse_args()


def stable_id(project_id: str, suffix: str) -> str:
    digest = hashlib.sha1(f"{project_id}:{suffix}".encode("utf-8")).hexdigest()[:12]
    return f"mem-project-{suffix}-{digest}"


def keywords_from_text(*texts: str, limit: int = 8) -> list[str]:
    counts: dict[str, int] = {}
    for text in texts:
        for token in tokenize(text):
            if len(token) <= 1 or token in STOPWORDS:
                continue
            counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [token for token, _ in ranked[:limit]]


def read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def summarize_skill(path: Path, project_name: str) -> tuple[str, list[str]]:
    lines = read_lines(path)
    description = next((line.split(":", 1)[1].strip() for line in lines if line.startswith("description:")), "")
    path_a = next((line for line in lines if "Path A" in line and "HTML" in line), "")
    path_b = next((line for line in lines if "Path B" in line and "AI" in line), "")
    mode_rows = [line for line in lines if "Full Auto" in line or "Guided" in line or "Collaborative" in line][:3]
    clean_modes = []
    for row in mode_rows:
        cleaned = row.replace("|", " ").replace("*", " ").strip()
        for label in ("Full Auto", "Guided", "Collaborative"):
            if label in cleaned and label not in clean_modes:
                clean_modes.append(label)
    summary = normalize_text(
        f"{project_name} 是一套 AI 演示文稿全流程工作流。{description} 默认走 Path A 可编辑 HTML 转 PPTX，也支持 Path B 全 AI 视觉图转 PPTX。"
        f"协作模式包含 {' / '.join(clean_modes) if clean_modes else 'Full Auto、Guided、Collaborative'}。"
        f"{path_a} {path_b}"
    )[:260]
    return summary, keywords_from_text(summary, description, path_a, path_b)


def summarize_input_outline(path: Path, project_name: str) -> tuple[str, list[str]]:
    lines = read_lines(path)
    slide_titles = [line.replace("**", "") for line in lines if line.startswith("**Slide")][:12]
    key_points = [line for line in lines if "可追溯" in line or "Log" in line or "工作流" in line][:5]
    summary = normalize_text(
        f"{project_name} 的课程输入大纲围绕 Dify 财务工作流实战训练营展开，包含课前导入、AI选型、节点地图、财务工作流案例、Workshop 实操等模块。"
        f"前几张关键页包括：{'；'.join(slide_titles[:6])}。"
        f"重点强调：{'；'.join(key_points)}"
    )[:260]
    return summary, keywords_from_text(summary, *slide_titles, *key_points)


def summarize_prompt_templates(path: Path, project_name: str) -> tuple[str, list[str]]:
    lines = read_lines(path)
    headings = [line.lstrip("# ").strip() for line in lines if line.startswith("## ") or line.startswith("### ")][:10]
    summary = normalize_text(
        f"{project_name} 内置演示文稿提示词模板库，覆盖完整大纲生成、商务汇报、培训课件、年度复盘、研究转演示、长文档转 Slides。"
        f"同时定义 Path A 的 html2pptx 物理约束，用于保证可编辑 PPT 导出稳定。"
        f"模板章节包括：{'；'.join(headings[:8])}。"
    )[:260]
    return summary, keywords_from_text(summary, *headings)


def build_project_entry_content(
    project_name: str,
    project_id: str,
    skill_summary: str,
    outline_summary: str,
    prompt_summary: str,
) -> str:
    return (
        f"# {project_name} 项目入口\n\n"
        f"- project_id: {project_id}\n"
        f"- 入口目标：作为该项目每次轻量进入时的固定首读摘要。\n\n"
        "## 先看什么\n"
        "1. 项目工作流总览\n"
        "2. 当前课程或内容结构\n"
        "3. 提示词模板与导出约束\n\n"
        "## 默认读取原则\n"
        "- 先读项目入口摘要，再按需读取项目 procedural / dynamic 记忆。\n"
        "- 当前 task 与当前 project 优先于 global 相似经验。\n"
        "- 需要原文证据时，再回源到项目原始文档。\n\n"
        "## 当前项目关键摘要\n"
        f"- 工作流：{skill_summary}\n"
        f"- 内容结构：{outline_summary}\n"
        f"- 模板与约束：{prompt_summary}\n"
    )


def main() -> None:
    args = parse_args()
    app = MemorySystemApp(ROOT)
    app.initialize()
    config = ConfigBundle(ROOT)
    archive = ArchiveStore(config.memory["paths"]["archive_root"])
    project_path = Path(args.project_path)
    scope = f"project:{args.project_id}"

    skill_path = project_path / "SKILL.md"
    input_outline_path = project_path.parent / "input.md"
    prompt_templates_path = project_path / "references" / "prompt-templates.md"

    skill_summary, skill_keywords = summarize_skill(skill_path, args.project_name)
    outline_summary, outline_keywords = summarize_input_outline(input_outline_path, args.project_name)
    prompt_summary, prompt_keywords = summarize_prompt_templates(prompt_templates_path, args.project_name)
    project_entry_content = build_project_entry_content(
        args.project_name,
        args.project_id,
        skill_summary,
        outline_summary,
        prompt_summary,
    )
    project_entry_path = archive.write_text(
        f"projects/{args.project_id}/project_entry.md",
        project_entry_content,
    )

    items = [
        MemoryItem(
            memory_id=stable_id(args.project_id, "entry"),
            layer="core",
            memory_type="project_profile",
            scope=scope,
            title=f"{args.project_name} 项目入口摘要",
            summary=normalize_text(
                f"{args.project_name} 的固定首读入口。先看工作流，再看内容结构和模板约束。默认项目优先于全局相似经验，"
                f"需要证据时再回项目原文。"
            )[:220],
            keywords=keywords_from_text(args.project_name, skill_summary, outline_summary, prompt_summary),
            source_refs=[project_entry_path],
            importance=0.96,
            confidence=0.94,
            strength=0.92,
            auto_inject_level="same_scope_only",
            delivery_options={
                "keyword_hint": ["项目入口", "工作流", "内容结构", "模板约束"],
                "method_summary": "先看项目工作流总览，再按需展开内容结构与模板约束；项目记忆优先于全局相似经验。",
            },
        ),
        MemoryItem(
            memory_id=stable_id(args.project_id, "workflow"),
            layer="procedural",
            memory_type="procedure",
            scope=scope,
            title=f"{args.project_name} 工作流总览",
            summary=skill_summary,
            keywords=skill_keywords,
            source_refs=[str(skill_path)],
            importance=0.92,
            confidence=0.90,
            strength=0.88,
            auto_inject_level="same_scope_only",
            delivery_options={
                "keyword_hint": skill_keywords[:4],
                "method_summary": skill_summary,
                "reusable_pattern": "默认 Path A 可编辑 HTML -> PPTX；需要视觉统一时走 Path B 全 AI 视觉图 -> PPTX。",
            },
        ),
        MemoryItem(
            memory_id=stable_id(args.project_id, "course-outline"),
            layer="dynamic",
            memory_type="knowledge",
            scope=scope,
            title=f"{args.project_name} 课程内容结构",
            summary=outline_summary,
            keywords=outline_keywords,
            source_refs=[str(input_outline_path)],
            importance=0.86,
            confidence=0.86,
            strength=0.82,
            auto_inject_level="explicit_only",
            delivery_options={
                "keyword_hint": outline_keywords[:4],
                "method_summary": outline_summary,
            },
        ),
        MemoryItem(
            memory_id=stable_id(args.project_id, "prompt-templates"),
            layer="dynamic",
            memory_type="knowledge",
            scope=scope,
            title=f"{args.project_name} 提示词与导出约束",
            summary=prompt_summary,
            keywords=prompt_keywords,
            source_refs=[str(prompt_templates_path)],
            importance=0.84,
            confidence=0.87,
            strength=0.80,
            auto_inject_level="same_scope_only",
            delivery_options={
                "keyword_hint": prompt_keywords[:4],
                "method_summary": prompt_summary,
            },
        ),
    ]

    for item in items:
        app.store.upsert_memory(item)

    print(
        json.dumps(
            {
                "status": "ok",
                "project_id": args.project_id,
                "project_name": args.project_name,
                "scope": scope,
                "imported_memory_ids": [item.memory_id for item in items],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
