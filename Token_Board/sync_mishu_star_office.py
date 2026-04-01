from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.loader import discover_agent_session_files, load_sessions
from src.utils import utc_now


AGENT_ID = os.environ.get("STAR_OFFICE_AGENT_ID", "mishu")
POLL_SECONDS = int(os.environ.get("STAR_OFFICE_SYNC_INTERVAL", "15"))
TTL_SECONDS = int(os.environ.get("STAR_OFFICE_STATE_TTL", "300"))
TICKER_MAX_CHARS = int(os.environ.get("STAR_OFFICE_TICKER_MAX_CHARS", "800"))
STATE_FILE = Path(
    os.environ.get(
        "STAR_OFFICE_STATE_FILE",
        Path(__file__).resolve().parent / "vendor" / "Star-Office-UI" / "state.json",
    )
)

USER_STREAMS = {"用户会话", "斜杠入口"}
PASSIVE_STREAMS = {"自动任务", "心跳巡检", "演化引擎", "系统会话"}
ACTIVE_REPLY_MARKERS = (
    "推进中", "在修", "修复", "处理中", "执行中", "正在推进", "持续推进", "排查", "调查", "验证中",
    "优化中", "还没修好", "未达到可验收", "落实中",
)
COMPLETED_REPLY_MARKERS = (
    "已完成", "已按", "已把", "已写入", "已落到", "已提交", "请秘书审核", "可审核证据",
    "会保持静默", "主动发你", "先回秘书", "等待下一步", "等审核", "已整理", "已回传",
)
BLOCKED_REPLY_MARKERS = (
    "blocker", "阻塞", "未解锁", "仍未收到", "未收到", "需要秘书", "需要管理员", "待提供",
    "待授权", "权限", "授权", "wiki 链接", "token",
)
SYNC_REPLY_MARKERS = ("同步中", "备份中", "上传中", "写回中", "落库中")


def latest_record(agent_id: str):
    payload = load_sessions(force=True, agent_ids=[agent_id])
    records = payload.get("records") or []
    if not records:
        return None
    return max(records, key=lambda record: record.last_active_at.timestamp() if record.last_active_at else 0)


def map_state(record) -> tuple[str, str]:
    if record is None or record.last_active_at is None:
        return "idle", "待命中，暂未观测到新会话"

    age_seconds = max(0, int((utc_now() - record.last_active_at).total_seconds()))
    age_minutes = age_seconds // 60
    latest_turn_tokens = record.recent_turns[0]["tokens"] if record.recent_turns else 0

    if record.workstream == "子代理执行":
        return "executing", f"正在推进执行任务 · 最近一轮 {latest_turn_tokens:,} tokens"
    if record.workstream in USER_STREAMS:
        return "writing", f"正在处理用户会话 · 最近一轮 {latest_turn_tokens:,} tokens"
    if record.workstream in PASSIVE_STREAMS:
        if age_minutes <= 15:
            return "idle", f"最近完成一轮内部处理 · {age_minutes} 分钟前更新"
        return "idle", f"待命中 · 最近更新于 {age_minutes} 分钟前"
    if age_minutes <= 90:
        return "researching", f"最近 {age_minutes} 分钟内有活动"
    return "idle", f"待命中 · 最近更新于 {age_minutes} 分钟前"


def state_from_reply(reply_text: str, fallback_state: str, fallback_detail: str) -> tuple[str, str]:
    reply = (reply_text or "").strip()
    if not reply:
        return fallback_state, fallback_detail

    normalized = reply.lower()
    if any(marker in normalized for marker in BLOCKED_REPLY_MARKERS):
        return "error", "当前存在阻塞，等待外部输入"
    if any(marker in reply for marker in SYNC_REPLY_MARKERS):
        return "syncing", "正在进行同步或备份"
    if any(marker in reply for marker in ACTIVE_REPLY_MARKERS):
        return "executing", "正在持续推进任务"
    if any(marker in reply for marker in COMPLETED_REPLY_MARKERS):
        return "idle", "已提交结果，等待下一步"
    return fallback_state, fallback_detail


def _active_agents_root() -> Optional[Path]:
    _, active_root = discover_agent_session_files()
    if active_root and active_root != "None":
        return Path(active_root)
    return None


def _resolve_session_file(session_file: Optional[str]) -> Optional[Path]:
    if not session_file:
        return None

    direct = Path(session_file)
    if direct.exists():
        return direct

    active_root = _active_agents_root()
    if not active_root:
        return None

    unix_prefix = "/state/agents/"
    if session_file.startswith(unix_prefix):
        relative = session_file[len(unix_prefix) :].replace("/", os.sep)
        candidate = active_root / relative
        if candidate.exists():
            return candidate

    return None


def _extract_text_parts(content) -> str:
    chunks = []
    for item in content or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "text" and item.get("text"):
            chunks.append(str(item["text"]))
    return "\n".join(chunks)


def _normalize_ticker_text(text: str) -> str:
    if not text:
        return ""

    normalized = text.replace("[[reply_to_current]]", " ")
    normalized = re.sub(r"`{3,}.*?`{3,}", " ", normalized, flags=re.DOTALL)
    normalized = re.sub(r"^#+\s*", "", normalized, flags=re.MULTILINE)
    normalized = normalized.replace("\r", "\n")
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    normalized = re.sub(r"\n{2,}", "  ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if len(normalized) > TICKER_MAX_CHARS:
        normalized = normalized[: TICKER_MAX_CHARS - 1].rstrip() + "…"
    return normalized


def latest_assistant_reply(record) -> str:
    session_path = _resolve_session_file(getattr(record, "session_file", None))
    if not session_path or not session_path.exists():
        return ""

    latest_text = ""
    try:
        with session_path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except Exception:
                    continue
                message = payload.get("message") or {}
                if message.get("role") != "assistant":
                    continue
                text = _normalize_ticker_text(_extract_text_parts(message.get("content") or []))
                if text:
                    latest_text = text
    except Exception:
        return ""

    return latest_text


def write_state(state: str, detail: str, ticker_text: str) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "state": state,
        "detail": detail,
        "ticker_text": ticker_text,
        "progress": 0,
        "ttl_seconds": TTL_SECONDS,
        "updated_at": datetime.now().isoformat(),
        "agent_id": AGENT_ID,
    }
    STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    print(f"[star-office-sync] agent={AGENT_ID} state_file={STATE_FILE}")
    while True:
        try:
            record = latest_record(AGENT_ID)
            ticker_text = latest_assistant_reply(record) if record else ""
            state, detail = map_state(record)
            state, detail = state_from_reply(ticker_text, state, detail)
            write_state(state, detail, ticker_text)
            preview = ticker_text[:80] + ("…" if len(ticker_text) > 80 else "") if ticker_text else "(no reply text)"
            print(f"[star-office-sync] {state} :: {detail} :: {preview}")
        except Exception as exc:
            print(f"[star-office-sync] error :: {exc}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
