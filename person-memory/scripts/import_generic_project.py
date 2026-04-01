from __future__ import annotations

import argparse
import hashlib
import json
import re
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
    "from",
    "into",
    "your",
    "project",
    "openclaw",
    "using",
    "使用",
    "项目",
    "一个",
    "这个",
    "那个",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="导入通用代码项目为项目级记忆")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--project-path", required=True)
    return parser.parse_args()


def stable_id(project_id: str, suffix: str) -> str:
    digest = hashlib.sha1(f"{project_id}:{suffix}".encode("utf-8")).hexdigest()[:12]
    return f"mem-generic-{suffix}-{digest}"


def keywords_from_text(*texts: str, limit: int = 8) -> list[str]:
    counts: dict[str, int] = {}
    for text in texts:
        for token in tokenize(text):
            if len(token) <= 1 or token in STOPWORDS:
                continue
            counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [token for token, _ in ranked[:limit]]


def read_text(path: Path, limit: int = 2000) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")[:limit]
    except UnicodeDecodeError:
        return ""


def detect_primary_files(project_path: Path) -> dict[str, Path]:
    candidates = {
        "readme": project_path / "README.md",
        "pyproject": project_path / "pyproject.toml",
        "package": project_path / "package.json",
        "skill": project_path / "SKILL.md",
    }
    return {name: path for name, path in candidates.items() if path.exists()}


def detect_structure(project_path: Path) -> list[str]:
    names = []
    for name in ("src", "app", "apps", "packages", "tests", "docs", "scripts"):
        if (project_path / name).exists():
            names.append(name)
    return names


def summarize_overview(project_name: str, files: dict[str, Path], structure: list[str]) -> tuple[str, list[str]]:
    readme_text = read_text(files.get("readme", Path()))
    first_paragraph = ""
    if readme_text:
        paragraphs = [normalize_text(block) for block in re.split(r"\n\s*\n", readme_text) if block.strip()]
        first_paragraph = paragraphs[0] if paragraphs else ""
    pyproject_text = read_text(files.get("pyproject", Path()), 500)
    package_text = read_text(files.get("package", Path()), 500)
    summary = normalize_text(
        f"{project_name} 是 openclaw 下的通用项目。"
        f"{first_paragraph} "
        f"{'项目结构包含：' + '、'.join(structure) + '。' if structure else '当前目录结构尚未形成明显分层。'} "
        f"{'检测到 pyproject 配置。' if pyproject_text else ''}"
        f"{'检测到 package.json。' if package_text else ''}"
    )[:260]
    return summary, keywords_from_text(summary, first_paragraph, " ".join(structure))


def summarize_structure(project_name: str, structure: list[str], files: dict[str, Path]) -> tuple[str, list[str]]:
    commands = []
    if "pyproject" in files:
        commands.append("优先看 pyproject.toml 和 src/tests 结构")
    if "package" in files:
        commands.append("优先看 package.json、src 和 scripts")
    if "skill" in files:
        commands.append("优先看 SKILL.md 的工作流定义")
    if not commands:
        commands.append("先看 README，再看 src、tests、scripts 的职责边界")
    summary = normalize_text(
        f"{project_name} 的项目进入顺序建议是："
        f"{'；'.join(commands)}。"
        f"{'当前可见目录：' + '、'.join(structure) + '。' if structure else ''}"
    )[:260]
    return summary, keywords_from_text(summary, *commands, " ".join(structure))


def summarize_artifacts(project_name: str, project_path: Path, files: dict[str, Path]) -> tuple[str, list[str]]:
    top_files = sorted(
        [
            path.name
            for path in project_path.iterdir()
            if path.is_file() and path.name not in {".DS_Store"}
        ]
    )[:12]
    summary = normalize_text(
        f"{project_name} 当前重要文件包括：{'、'.join(top_files) if top_files else '暂无关键文件'}。"
        f"{'检测到 README.md。' if 'readme' in files else ''}"
        f"{'检测到 pyproject.toml。' if 'pyproject' in files else ''}"
        f"{'检测到 package.json。' if 'package' in files else ''}"
    )[:240]
    return summary, keywords_from_text(summary, " ".join(top_files))


def build_project_entry(project_name: str, project_id: str, overview: str, structure: str, artifacts: str) -> str:
    return (
        f"# {project_name} 项目入口\n\n"
        f"- project_id: {project_id}\n"
        "- 项目类型：openclaw 通用代码项目\n\n"
        "## 首读顺序\n"
        "1. README 或主说明文件\n"
        "2. 项目结构与关键配置\n"
        "3. 关键文件与当前可见目录\n\n"
        "## 默认读取原则\n"
        "- 先读项目入口摘要，再按需读取项目 overview / structure / artifacts 记忆。\n"
        "- 如果项目后续形成真实会话，再导入会话经验。\n"
        "- 如需精确结论，再回项目原始文件。\n\n"
        "## 当前项目摘要\n"
        f"- 概览：{overview}\n"
        f"- 结构：{structure}\n"
        f"- 文件与产物：{artifacts}\n"
    )


def main() -> None:
    args = parse_args()
    app = MemorySystemApp(ROOT)
    app.initialize()
    config = ConfigBundle(ROOT)
    archive = ArchiveStore(config.memory["paths"]["archive_root"])

    project_path = Path(args.project_path)
    scope = f"project:{args.project_id}"
    files = detect_primary_files(project_path)
    structure = detect_structure(project_path)
    overview_summary, overview_keywords = summarize_overview(args.project_name, files, structure)
    structure_summary, structure_keywords = summarize_structure(args.project_name, structure, files)
    artifact_summary, artifact_keywords = summarize_artifacts(args.project_name, project_path, files)

    entry_content = build_project_entry(
        args.project_name,
        args.project_id,
        overview_summary,
        structure_summary,
        artifact_summary,
    )
    entry_path = archive.write_text(f"projects/{args.project_id}/project_entry.md", entry_content)

    items = [
        MemoryItem(
            memory_id=stable_id(args.project_id, "entry"),
            layer="core",
            memory_type="project_profile",
            scope=scope,
            title=f"{args.project_name} 项目入口摘要",
            summary=normalize_text(
                f"{args.project_name} 的固定首读入口。先看 README 和关键配置，再看项目结构与关键文件。"
            )[:220],
            keywords=keywords_from_text(args.project_name, overview_summary, structure_summary, artifact_summary),
            source_refs=[entry_path],
            importance=0.94,
            confidence=0.90,
            strength=0.86,
            auto_inject_level="same_scope_only",
            delivery_options={
                "keyword_hint": ["项目入口", "README", "项目结构", "关键文件"],
                "method_summary": "先看 README 和关键配置，再看结构和关键文件；需要精确结论时回项目原始文件。",
            },
        ),
        MemoryItem(
            memory_id=stable_id(args.project_id, "overview"),
            layer="dynamic",
            memory_type="knowledge",
            scope=scope,
            title=f"{args.project_name} 项目概览",
            summary=overview_summary,
            keywords=overview_keywords,
            source_refs=[str(path) for path in files.values()],
            importance=0.86,
            confidence=0.82,
            strength=0.78,
            auto_inject_level="same_scope_only",
            delivery_options={
                "keyword_hint": overview_keywords[:4],
                "method_summary": overview_summary,
            },
        ),
        MemoryItem(
            memory_id=stable_id(args.project_id, "structure"),
            layer="procedural",
            memory_type="procedure",
            scope=scope,
            title=f"{args.project_name} 结构与进入顺序",
            summary=structure_summary,
            keywords=structure_keywords,
            source_refs=[str(path) for path in files.values()],
            importance=0.88,
            confidence=0.84,
            strength=0.80,
            auto_inject_level="same_scope_only",
            delivery_options={
                "keyword_hint": structure_keywords[:4],
                "method_summary": structure_summary,
                "reusable_pattern": structure_summary,
            },
        ),
        MemoryItem(
            memory_id=stable_id(args.project_id, "artifacts"),
            layer="dynamic",
            memory_type="knowledge",
            scope=scope,
            title=f"{args.project_name} 关键文件与产物",
            summary=artifact_summary,
            keywords=artifact_keywords,
            source_refs=[str(project_path)],
            importance=0.80,
            confidence=0.80,
            strength=0.72,
            auto_inject_level="explicit_only",
            delivery_options={
                "keyword_hint": artifact_keywords[:4],
                "method_summary": artifact_summary,
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
                "project_path": str(project_path),
                "imported_memory_ids": [item.memory_id for item in items],
                "detected_files": {name: str(path) for name, path in files.items()},
                "detected_structure": structure,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
