from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Any, Dict, List, Optional, Tuple

from .utils import parse_datetime, to_int

PROJECT_PATTERNS = [
    re.compile(r'BotProjects[\\/](?P<name>[A-Za-z0-9._-]+)', re.IGNORECASE),
    re.compile(r'--tag\s+(?P<tag>[A-Za-z0-9._-]+)', re.IGNORECASE),
    re.compile(r'(?:project|项目)\s*[:：=]\s*(?P<label>[A-Za-z0-9._-]+)', re.IGNORECASE),
]


@dataclass
class SessionRecord:
    session_key: str
    session_type: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    last_active_at: Optional[datetime]
    agent_id: Optional[str] = None
    channel: str = 'unknown'
    provider: str = 'unknown'
    runtime_provider: str = 'unknown'
    runtime_model: str = 'unknown'
    runtime_auth_profile: str = ''
    runtime_auth_account: str = ''
    runtime_account_id: str = ''
    workstream: str = '系统会话'
    project: str = '未标记'
    project_source: str = '未标记'
    session_file: Optional[str] = None
    delivery_target: str = ''
    aborted_last_run: bool = False
    system_sent: bool = False
    assistant_turns: int = 0
    recent_5m_tokens: int = 0
    recent_1h_tokens: int = 0
    recent_24h_tokens: int = 0
    tool_error_count: int = 0
    error_turn_count: int = 0
    error_turn_tokens: int = 0
    first_user_text: str = ''
    model_breakdown: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    recent_turns: List[Dict[str, Any]] = field(default_factory=list)


def extract_project_hint(text: str) -> Tuple[str, str]:
    if not text:
        return '未标记', '未标记'
    for pattern in PROJECT_PATTERNS:
        match = pattern.search(text)
        if match:
            value = match.groupdict().get('name') or match.groupdict().get('tag') or match.groupdict().get('label')
            if value:
                return value, '显式标签'
    if 'Token_Board' in text or 'Token Board' in text:
        return 'Token_Board', '文本命中'
    return '未标记', '未标记'


def classify_workstream(session_key: str, origin: Dict[str, Any], channel: str) -> str:
    key = session_key or ''
    provider = str(origin.get('provider') or '').lower()
    surface = str(origin.get('surface') or '').lower()
    channel_name = str(channel or '').lower()

    if ':subagent:' in key or provider == 'subagent':
        return '子代理执行'
    if 'heartbeat' in key or provider == 'heartbeat':
        return '心跳巡检'
    if ':cron:' in key or provider == 'cron':
        return '自动任务'
    if 'evolver' in key:
        return '演化引擎'
    if ':slash:' in key or channel_name == 'slash':
        return '斜杠入口'
    if ':telegram:' in key or surface in ('telegram', 'discord', 'feishu', 'whatsapp'):
        return '用户会话'
    return '系统会话'


def parse_record(row: Dict[str, Any], fallback_session_key: Optional[str] = None) -> Optional[SessionRecord]:
    if not isinstance(row, dict):
        return None

    try:
        origin = row.get('origin') or {}
        delivery = row.get('deliveryContext') or {}
        input_t = to_int(row.get('inputTokens'))
        output_t = to_int(row.get('outputTokens'))
        total_t = to_int(row.get('totalTokens') or row.get('tokens') or (input_t + output_t))
        session_key = fallback_session_key or row.get('sessionId', 'unknown')
        channel = delivery.get('channel') or row.get('lastChannel') or origin.get('surface') or origin.get('provider') or 'unknown'
        project, source = extract_project_hint(session_key)
        auth_profile = str(row.get('authProfileOverride') or '')
        auth_account = auth_profile.split(':', 1)[1] if ':' in auth_profile else auth_profile
        runtime_provider = str(row.get('modelProvider') or row.get('providerOverride') or 'unknown')
        runtime_model = str(row.get('model') or row.get('modelOverride') or 'unknown')
        runtime_account_id = str(origin.get('accountId') or delivery.get('accountId') or '')

        return SessionRecord(
            session_key=session_key,
            session_type=row.get('chatType') or origin.get('chatType') or 'direct',
            input_tokens=input_t,
            output_tokens=output_t,
            total_tokens=total_t,
            cache_read_tokens=to_int(row.get('cacheRead')),
            cache_write_tokens=to_int(row.get('cacheWrite')),
            last_active_at=parse_datetime(row.get('updatedAt')),
            channel=str(channel),
            provider=str(origin.get('provider') or origin.get('surface') or 'unknown'),
            runtime_provider=runtime_provider,
            runtime_model=runtime_model,
            runtime_auth_profile=auth_profile,
            runtime_auth_account=auth_account,
            runtime_account_id=runtime_account_id,
            workstream=classify_workstream(session_key, origin, str(channel)),
            project=project,
            project_source=source,
            session_file=row.get('sessionFile'),
            delivery_target=str(delivery.get('to') or row.get('lastTo') or origin.get('to') or ''),
            aborted_last_run=bool(row.get('abortedLastRun')),
            system_sent=bool(row.get('systemSent')),
        )
    except Exception:
        return None
