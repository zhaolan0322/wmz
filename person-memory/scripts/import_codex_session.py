from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

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
    "主要",
    "然后",
    "以及",
    "因为",
    "如果",
    "使用",
    "进行",
    "支持",
    "流程",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="导入 Codex 会话日志到个人记忆系统")
    parser.add_argument("--session-id", required=True, help="Codex 会话 ID")
    parser.add_argument("--project-id", default=None, help="导入后的项目 ID，如 huashu-slides")
    parser.add_argument("--task-id", default=None, help="导入后的任务 ID")
    parser.add_argument("--project-path", default=None, help="相关项目路径，可用于补充项目线索")
    return parser.parse_args()


def codex_home() -> Path:
    return Path.home() / ".codex"


def locate_session_file(session_id: str) -> Path:
    session_root = codex_home() / "sessions"
    matches = list(session_root.rglob(f"*{session_id}*.jsonl"))
    if not matches:
        raise FileNotFoundError(f"未找到会话文件: {session_id}")
    return matches[0]


def lookup_thread_name(session_id: str) -> str:
    index_path = codex_home() / "session_index.jsonl"
    if not index_path.exists():
        return ""
    for line in index_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("id") == session_id:
            return record.get("thread_name", "")
    return ""


def extract_text_parts(content: list[dict]) -> str:
    parts: list[str] = []
    for item in content or []:
        text = item.get("text") or item.get("input_text") or item.get("output_text")
        if text:
            parts.append(text)
    return normalize_text("\n".join(parts))


def parse_session_messages(session_path: Path) -> dict:
    users: list[str] = []
    assistants: list[str] = []
    session_meta: dict = {}
    for raw_line in session_path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        try:
            item = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if item.get("type") == "session_meta":
            session_meta = item.get("payload", {})
            continue
        if item.get("type") != "response_item":
            continue
        payload = item.get("payload", {})
        if payload.get("type") != "message":
            continue
        role = payload.get("role")
        text = extract_text_parts(payload.get("content", []))
        if not text:
            continue
        if role == "user":
            users.append(text)
        elif role == "assistant":
            assistants.append(text)
    return {
        "users": users,
        "assistants": assistants,
        "session_meta": session_meta,
    }


def top_keywords(*texts: str, limit: int = 8) -> list[str]:
    counts: dict[str, int] = {}
    for text in texts:
        for token in tokenize(text):
            if len(token) <= 1 or token in STOPWORDS:
                continue
            counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [token for token, _ in ranked[:limit]]


def build_summary(thread_name: str, users: list[str], assistants: list[str], project_path: str | None) -> str:
    last_user = users[-1] if users else ""
    last_assistant = assistants[-1] if assistants else ""
    project_note = ""
    if project_path:
        skill_md = Path(project_path) / "SKILL.md"
        if skill_md.exists():
            first_lines = skill_md.read_text(encoding="utf-8").splitlines()[:20]
            project_note = normalize_text(" ".join(first_lines))
    parts = [part for part in [thread_name, last_user, last_assistant, project_note] if part]
    summary = normalize_text(" ".join(parts))
    return summary[:420]


def build_learned_summary(thread_name: str, users: list[str], assistants: list[str]) -> str:
    focus_window = users[-6:] + assistants[-3:]
    focus_text = normalize_text(" ".join(focus_window))
    keywords = top_keywords(thread_name, focus_text, limit=6)
    keyword_line = "、".join(keywords)
    last_answer = assistants[-1] if assistants else ""
    summary = normalize_text(
        f"{thread_name}。会话主题集中在：{keyword_line}。"
        f"{last_answer}"
    )
    return summary[:320]


def project_scope_for_session(project_id: str | None, thread_name: str, users: list[str], assistants: list[str], project_path: str | None) -> str:
    if not project_id:
        return "global"
    signals = [thread_name, " ".join(users[-2:]), " ".join(assistants[-1:])]
    merged = normalize_text(" ".join(part for part in signals if part)).lower()
    if project_id.lower() in merged:
        return f"project:{project_id}"
    return "global"


def summarize_skill_project(project_path: Path) -> tuple[str, list[str]]:
    skill_md = project_path / "SKILL.md"
    if not skill_md.exists():
        return "", []
    text = skill_md.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    description = ""
    for line in lines:
        if line.startswith("description:"):
            description = line.split(":", 1)[1].strip()
            break
    trigger_line = next((line for line in lines if "做PPT" in line or "演示文稿" in line), "")
    path_a = next((line for line in lines if "Path A" in line and "HTML" in line), "")
    path_b = next((line for line in lines if "Path B" in line and "AI" in line), "")
    mode_line = next((line for line in lines if "Full Auto" in line and "Guided" in line), "")
    summary_parts = [
        project_path.name,
        description,
        "默认支持 Path A 可编辑 HTML 转 PPTX。",
        "同时支持 Path B 全 AI 视觉图转 PPTX。",
        "协作模式包含 Full Auto、Guided、Collaborative。",
    ]
    if trigger_line:
        summary_parts.append(trigger_line)
    if path_a:
        summary_parts.append(path_a)
    if path_b:
        summary_parts.append(path_b)
    if mode_line:
        summary_parts.append(mode_line)
    summary = normalize_text(" ".join(summary_parts))[:260]
    return summary, top_keywords(summary, description, trigger_line, path_a, path_b)


def derive_delivery_options(summary: str, keywords: list[str]) -> dict:
    return {
        "keyword_hint": keywords[:4],
        "method_summary": summary[:220],
        "reusable_pattern": summary[:220],
    }


def stable_memory_id(prefix: str, session_id: str) -> str:
    digest = hashlib.sha1(f"{prefix}:{session_id}".encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def main() -> None:
    args = parse_args()
    app = MemorySystemApp(ROOT)
    app.initialize()
    config = ConfigBundle(ROOT)
    archive = ArchiveStore(config.memory["paths"]["archive_root"])

    session_path = locate_session_file(args.session_id)
    thread_name = lookup_thread_name(args.session_id)
    parsed = parse_session_messages(session_path)
    users = parsed["users"]
    assistants = parsed["assistants"]

    if not users and not assistants:
        raise RuntimeError("会话中未解析到可用消息")

    conversation_scope = project_scope_for_session(args.project_id, thread_name, users, assistants, args.project_path)
    project_scope = f"project:{args.project_id}" if args.project_id else "global"
    raw_archive_path = archive.write_text(
        f"imports/codex/{args.session_id}.jsonl",
        session_path.read_text(encoding="utf-8"),
    )

    summary = build_summary(thread_name, users, assistants, args.project_path)
    keywords = top_keywords(thread_name, users[-1] if users else "", assistants[-1] if assistants else "", summary)

    conversation_memory = MemoryItem(
        memory_id=stable_memory_id("mem-import-codex-conv", args.session_id),
        layer="raw",
        memory_type="episode",
        scope=conversation_scope,
        title=thread_name or f"导入会话 {args.session_id}",
        summary=summary,
        keywords=keywords,
        source_refs=[f"archive://imports/codex/{args.session_id}.jsonl"],
        importance=0.72,
        confidence=0.85,
        strength=0.70,
        auto_inject_level="never",
        delivery_options={"keyword_hint": keywords[:4]},
    )
    app.store.upsert_memory(conversation_memory)

    if assistants:
        learned_summary = build_learned_summary(thread_name, users, assistants)
        learned_keywords = top_keywords(thread_name, learned_summary, " ".join(users[-6:]), limit=8)
        learned_memory = MemoryItem(
            memory_id=stable_memory_id("mem-import-codex-learned", args.session_id),
            layer="dynamic",
            memory_type="experience",
            scope=conversation_scope,
            title=(thread_name or "会话经验")[:80],
            summary=learned_summary,
            keywords=learned_keywords,
            source_refs=[raw_archive_path],
            importance=0.78,
            confidence=0.84,
            strength=0.76,
            auto_inject_level="explicit_only",
            delivery_options=derive_delivery_options(learned_summary, learned_keywords),
        )
        app.store.upsert_memory(learned_memory)

    project_memory_id = None
    if args.project_path:
        project_path = Path(args.project_path)
        skill_md = project_path / "SKILL.md"
        if skill_md.exists():
            project_summary, project_keywords = summarize_skill_project(project_path)
            project_memory = MemoryItem(
                memory_id=stable_memory_id("mem-import-project-skill", args.session_id),
                layer="procedural",
                memory_type="procedure",
                scope=project_scope,
                title=f"{project_path.name} 工作流",
                summary=project_summary,
                keywords=project_keywords,
                source_refs=[str(skill_md)],
                importance=0.86,
                confidence=0.88,
                strength=0.82,
                auto_inject_level="same_scope_only",
                delivery_options=derive_delivery_options(project_summary, project_keywords),
            )
            app.store.upsert_memory(project_memory)
            project_memory_id = project_memory.memory_id

    result = {
        "status": "ok",
        "session_id": args.session_id,
        "thread_name": thread_name,
        "conversation_scope": conversation_scope,
        "project_scope": project_scope,
        "raw_archive_path": raw_archive_path,
        "imported_memory_ids": [
            stable_memory_id("mem-import-codex-conv", args.session_id),
            stable_memory_id("mem-import-codex-learned", args.session_id) if assistants else None,
            project_memory_id,
        ],
    }
    result["imported_memory_ids"] = [item for item in result["imported_memory_ids"] if item]
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
