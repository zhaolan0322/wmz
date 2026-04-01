from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .parser import SessionRecord, extract_project_hint, parse_record
from .utils import parse_datetime, to_int, utc_now

OFFICIAL_BOTS = {'main', 'mishu', 'wangzai', 'jinbao', 'houqin', 'zhaocaixia'}

_cache = {
    'expires_at': 0.0,
    'key': None,
    'result': None,
}


def discover_agent_session_files() -> Tuple[List[Tuple[str, Path]], str]:
    candidate_roots = []
    for env_name in ('TOKEN_BOARD_AGENTS_ROOT', 'OPENCLAW_AGENTS_ROOT'):
        raw = os.getenv(env_name, '').strip()
        if raw:
            candidate_roots.append(Path(raw).expanduser())
    candidate_roots.extend([
        Path('/state/agents'),
        Path.home() / '.openclaw' / 'agents',
    ])
    active_root = None
    files = []
    for root in candidate_roots:
        if not root.exists():
            continue
        found = list(root.glob('*/sessions/sessions.json'))
        if not found:
            continue
        active_root = root
        for session_path in found:
            try:
                agent_id = session_path.parts[-3]
                if agent_id in OFFICIAL_BOTS:
                    files.append((agent_id, session_path))
            except Exception:
                continue
        break
    return sorted(files), str(active_root or 'None')


def _extract_text(content: List[Dict[str, Any]]) -> str:
    parts = []
    for item in content or []:
        if isinstance(item, dict) and item.get('type') == 'text':
            text = item.get('text')
            if text:
                parts.append(str(text))
    return '\n'.join(parts)


def _session_file_path(session_file: Optional[str], active_root: str) -> Optional[Path]:
    if not session_file:
        return None
    direct = Path(session_file)
    if direct.exists():
        return direct

    root = Path(active_root)
    if session_file.startswith('/state/agents/') and root.exists():
        suffix = session_file.split('/state/agents/', 1)[1].replace('/', os.sep)
        candidate = root / suffix
        if candidate.exists():
            return candidate
    return None


def _tool_result_is_error(obj: Dict[str, Any], message: Dict[str, Any]) -> bool:
    if obj.get('isError') or message.get('isError'):
        return True
    details = obj.get('details') or message.get('details') or {}
    if isinstance(details, dict) and details.get('status') == 'error':
        return True
    text = _extract_text(message.get('content') or []).lower()
    return (
        '"status": "error"' in text
        or 'validation failed for tool' in text
        or 'command aborted by signal' in text
        or 'enoent:' in text
    )


def _merge_model_usage(record: SessionRecord, model: str, provider: str, total_tokens: int, turn_tokens: int) -> None:
    key = model or 'unknown'
    bucket = record.model_breakdown.setdefault(key, {
        'provider': provider or 'unknown',
        'tokens': 0,
        'turns': 0,
    })
    bucket['tokens'] += total_tokens
    bucket['turns'] += turn_tokens


def _remember_recent_turn(record: SessionRecord, timestamp, total_tokens: int, session_key: str) -> None:
    if not timestamp or total_tokens <= 0:
        return
    record.recent_turns.append({
        'timestamp': timestamp,
        'tokens': total_tokens,
        'sessionKey': session_key,
    })
    record.recent_turns.sort(key=lambda item: item['timestamp'], reverse=True)
    if len(record.recent_turns) > 2:
        record.recent_turns = record.recent_turns[:2]


def _enrich_from_jsonl(record: SessionRecord, jsonl_path: Optional[Path], now_ts) -> None:
    if not jsonl_path or not jsonl_path.exists():
        return

    pending_calls = {}
    counted_error_turns = set()

    try:
        with open(jsonl_path, 'r', encoding='utf-8', errors='ignore') as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue

                message = obj.get('message') or {}
                role = message.get('role')
                timestamp = parse_datetime(obj.get('timestamp') or message.get('timestamp'))

                if role == 'user' and not record.first_user_text:
                    record.first_user_text = _extract_text(message.get('content') or [])[:4000]
                    project, source = extract_project_hint(record.first_user_text)
                    if project != '未标记':
                        record.project = project
                        record.project_source = source
                    elif 'Token_Board' in record.first_user_text or 'Token Board' in record.first_user_text:
                        record.project = 'Token_Board'
                        record.project_source = '文本命中'

                if role == 'assistant':
                    usage = message.get('usage') or {}
                    input_tokens = to_int(usage.get('inputTokens') or usage.get('input'))
                    output_tokens = to_int(usage.get('outputTokens') or usage.get('output'))
                    total_tokens = to_int(usage.get('totalTokens') or usage.get('total') or (input_tokens + output_tokens))
                    if total_tokens > 0:
                        record.assistant_turns += 1
                        _remember_recent_turn(record, timestamp, total_tokens, record.session_key)
                        if timestamp and timestamp >= now_ts['five_minutes']:
                            record.recent_5m_tokens += total_tokens
                        if timestamp and timestamp >= now_ts['one_hour']:
                            record.recent_1h_tokens += total_tokens
                        if timestamp and timestamp >= now_ts['one_day']:
                            record.recent_24h_tokens += total_tokens
                        _merge_model_usage(
                            record,
                            str(message.get('model') or 'unknown'),
                            str(message.get('provider') or 'unknown'),
                            total_tokens,
                            1,
                        )

                    turn_id = obj.get('id') or ''
                    for item in message.get('content') or []:
                        if isinstance(item, dict) and item.get('type') == 'toolCall' and item.get('id'):
                            pending_calls[item['id']] = {
                                'turn_id': turn_id,
                                'tokens': total_tokens,
                            }

                elif role == 'toolResult' and _tool_result_is_error(obj, message):
                    record.tool_error_count += 1
                    tool_call_id = message.get('toolCallId')
                    pending = pending_calls.get(tool_call_id)
                    if pending and pending['turn_id'] not in counted_error_turns:
                        counted_error_turns.add(pending['turn_id'])
                        record.error_turn_count += 1
                        record.error_turn_tokens += pending['tokens']
    except Exception:
        return


def _load_one(path: Path, agent_id: str, active_root: str):
    now = utc_now()
    from datetime import timedelta

    now_ts = {
        'five_minutes': now - timedelta(minutes=5),
        'one_hour': now - timedelta(hours=1),
        'one_day': now - timedelta(days=1),
    }

    chunk = {'agentId': agent_id, 'records': []}
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            raw = json.load(handle)
    except Exception:
        return chunk

    items = raw.items() if isinstance(raw, dict) else []
    for session_key, row in items:
        record = parse_record(row, fallback_session_key=session_key)
        if not record:
            continue
        record.agent_id = agent_id
        session_path = _session_file_path(record.session_file, active_root)
        _enrich_from_jsonl(record, session_path, now_ts)
        chunk['records'].append(record)
    return chunk


def _source_rows(records: List[SessionRecord]) -> List[Dict[str, Any]]:
    grouped = {}
    for record in records:
        item = grouped.setdefault(record.agent_id, {
            'agentId': record.agent_id,
            'sumTotalTokens': 0,
            'inputTokens': 0,
            'outputTokens': 0,
            'parsedSessions': 0,
            'recent5mTokens': 0,
            'recent24hTokens': 0,
            'errorTurnTokens': 0,
            'errorTurnCount': 0,
            'assistantTurns': 0,
        })
        item['sumTotalTokens'] += record.total_tokens
        item['inputTokens'] += record.input_tokens
        item['outputTokens'] += record.output_tokens
        item['parsedSessions'] += 1
        item['recent5mTokens'] += record.recent_5m_tokens
        item['recent24hTokens'] += record.recent_24h_tokens
        item['errorTurnTokens'] += record.error_turn_tokens
        item['errorTurnCount'] += record.error_turn_count
        item['assistantTurns'] += record.assistant_turns

    return sorted(grouped.values(), key=lambda row: row['sumTotalTokens'], reverse=True)


def load_sessions(force: bool = False, agent_ids: Optional[List[str]] = None):
    now_ts = time.time()
    cache_key = ','.join(sorted(agent_ids)) if agent_ids else 'all'
    if not force and _cache['key'] == cache_key and now_ts < _cache['expires_at']:
        return _cache['result']

    files, active_path = discover_agent_session_files()
    result = {
        'loadedAt': utc_now().isoformat(),
        'records': [],
        'sources': [],
        'path': active_path,
        'env': 'Container' if '/state/' in active_path else 'Host',
        'totalRawRows': 0,
    }

    selected = [item for item in files if item[0] in set(agent_ids or [])] if agent_ids else files
    for agent_id, file_path in selected:
        chunk = _load_one(file_path, agent_id, active_path)
        result['records'].extend(chunk['records'])
        result['totalRawRows'] += len(chunk['records'])

    result['sources'] = _source_rows(result['records'])
    _cache.update({
        'expires_at': now_ts + 10,
        'key': cache_key,
        'result': result,
    })
    return result
