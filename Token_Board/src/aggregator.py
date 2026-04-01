from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from .filters import in_range
from .loader import OFFICIAL_BOTS, load_sessions
from .utils import utc_now

VALID_RANGES = {'today', '7d', '30d', 'all'}
OPS_STREAMS = {'自动任务', '心跳巡检', '演化引擎', '子代理执行', '系统会话'}
USER_STREAMS = {'用户会话', '斜杠入口'}
OFFICE_AGENT_ORDER = ['mishu', 'wangzai', 'jinbao', 'houqin', 'zhaocaixia', 'main']


def _check_range(range_name: str) -> str:
    if range_name not in VALID_RANGES:
        raise ValueError('Unsupported range: {0}'.format(range_name))
    return range_name


def _filtered(range_name: str, agent_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    range_name = _check_range(range_name)
    payload = load_sessions(agent_ids=agent_ids)
    now = utc_now()
    records = [record for record in payload['records'] if in_range(record.last_active_at, range_name, now)]
    return {
        'range': range_name,
        'records': records,
        'loadedAt': payload['loadedAt'],
        'path': payload['path'],
        'totalRawRows': payload['totalRawRows'],
        'sources': payload['sources'],
        'env': payload.get('env', 'Unknown'),
    }


def _sort_rows(rows: List[Dict[str, Any]], key: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: row.get(key, 0), reverse=True)
    return ordered[:limit] if limit else ordered


def _effective_cost_center(record) -> Dict[str, str]:
    if record.project != '未标记':
        return {'name': record.project, 'source': record.project_source or '显式标签', 'kind': 'project'}
    return {'name': record.workstream, 'source': '成本归因', 'kind': 'workstream'}


def _is_productive(record) -> bool:
    return record.project != '未标记' or record.workstream in USER_STREAMS


def _daily_projection(records, days: int) -> int:
    if days <= 0:
        return 0
    total = sum(record.total_tokens for record in records)
    return int(round(total / float(days))) if total else 0


def _latest_turn_pair(records) -> List[Dict[str, Any]]:
    turns = []
    for record in records:
        for item in getattr(record, 'recent_turns', []) or []:
            timestamp = item.get('timestamp')
            if not timestamp:
                continue
            turns.append({
                'tokens': int(item.get('tokens', 0)),
                'timestamp': timestamp,
                'sessionKey': item.get('sessionKey') or record.session_key,
                'agentId': record.agent_id,
            })
    turns.sort(key=lambda item: item['timestamp'], reverse=True)
    return turns[:2]


def _latest_active_record(records):
    candidates = [record for record in records if record.last_active_at]
    if not candidates:
        return None
    return max(candidates, key=lambda record: record.last_active_at)


def _latest_records_by_agent(records):
    latest = {}
    for record in records:
        if not record.agent_id:
            continue
        current = latest.get(record.agent_id)
        if current is None or (
            record.last_active_at
            and (current.last_active_at is None or record.last_active_at > current.last_active_at)
        ):
            latest[record.agent_id] = record
    return latest


def _office_state(record, now):
    if record is None or record.last_active_at is None:
        return 'offline', '离线', '最近没有观测到活跃会话'

    age_seconds = max(0, int((now - record.last_active_at).total_seconds()))
    age_minutes = age_seconds // 60
    latest_turn_tokens = record.recent_turns[0]['tokens'] if record.recent_turns else 0

    if record.recent_5m_tokens >= 100000 or (record.error_turn_tokens > 0 and age_minutes <= 30):
        return 'error', '异常排障', '错误损耗 {0:,}'.format(record.error_turn_tokens or record.recent_5m_tokens)
    if record.workstream in {'自动任务', '心跳巡检', '演化引擎'}:
        return 'syncing', '系统巡检', '{0} · 近 1h {1:,}'.format(record.workstream, record.recent_1h_tokens)
    if record.workstream == '子代理执行':
        return 'executing', '执行任务', '近一轮 {0:,} tokens'.format(latest_turn_tokens)
    if record.workstream in USER_STREAMS:
        return 'writing', '用户对话', '近一轮 {0:,} tokens'.format(latest_turn_tokens)
    if age_minutes <= 90:
        return 'researching', '轻度活跃', '{0} 分钟内有活动'.format(age_minutes)
    if age_minutes <= 8 * 60:
        return 'idle', '待命中', '{0} 分钟前更新'.format(age_minutes)
    return 'offline', '离线', '{0} 小时前更新'.format(max(1, age_minutes // 60))


def _build_overview(data: Dict[str, Any]) -> Dict[str, Any]:
    records = data['records']
    total_tokens = sum(record.total_tokens for record in records)
    input_tokens = sum(record.input_tokens for record in records)
    output_tokens = sum(record.output_tokens for record in records)
    cache_read_tokens = sum(record.cache_read_tokens for record in records)
    cache_write_tokens = sum(record.cache_write_tokens for record in records)
    assistant_turns = sum(record.assistant_turns for record in records)
    observed_runtime_tokens = sum(
        sum(int(usage.get('tokens', 0)) for usage in (record.model_breakdown or {}).values())
        for record in records
    )
    productive_tokens = sum(record.total_tokens for record in records if _is_productive(record))
    ops_tokens = sum(record.total_tokens for record in records if record.workstream in OPS_STREAMS)
    error_tokens = sum(record.error_turn_tokens for record in records)
    recent_5m = sum(record.recent_5m_tokens for record in records)
    recent_1h = sum(record.recent_1h_tokens for record in records)
    recent_24h = sum(record.recent_24h_tokens for record in records)
    latest_record = _latest_active_record(records)
    latest_cache_input_tokens = latest_record.input_tokens if latest_record else 0
    latest_cache_read_tokens = latest_record.cache_read_tokens if latest_record else 0
    latest_cache_write_tokens = latest_record.cache_write_tokens if latest_record else 0
    cache_base_tokens = latest_cache_input_tokens + latest_cache_read_tokens + latest_cache_write_tokens
    cache_hit_rate = round((latest_cache_read_tokens / float(cache_base_tokens)) * 100) if cache_base_tokens else 0
    latest_turns = _latest_turn_pair(records)
    latest_turn = latest_turns[0] if len(latest_turns) > 0 else {}
    previous_turn = latest_turns[1] if len(latest_turns) > 1 else {}

    active_agents = len({record.agent_id for record in records})
    daily_burn = _daily_projection(records, {'today': 1, '7d': 7, '30d': 30, 'all': 30}.get(data['range'], 30))
    forecast_30d = daily_burn * 30

    threshold = 100000
    if recent_5m >= threshold:
        alert = {'level': 'critical', 'label': '红灯止损', 'message': '最近 5 分钟总消耗已超过阈值'}
    elif error_tokens > max(int(total_tokens * 0.12), 50000):
        alert = {'level': 'warning', 'label': '黄灯复盘', 'message': '错误暴露偏高，需要复盘流程与模型选择'}
    else:
        alert = {'level': 'normal', 'label': '运行稳定', 'message': '当前没有触发止损条件'}

    return {
        'range': data['range'],
        'sessions': len(records),
        'activeAgents': active_agents,
        'assistantTurns': assistant_turns,
        'inputTokens': input_tokens,
        'outputTokens': output_tokens,
        'cacheReadTokens': latest_cache_read_tokens,
        'cacheWriteTokens': latest_cache_write_tokens,
        'cacheInputTokens': latest_cache_input_tokens,
        'cacheBaseTokens': cache_base_tokens,
        'cacheHitRate': cache_hit_rate,
        'cacheScope': 'latest-active-session',
        'cacheSessionKey': latest_record.session_key if latest_record else None,
        'cacheUpdatedAt': latest_record.last_active_at.isoformat() if latest_record and latest_record.last_active_at else None,
        'cacheAgentId': latest_record.agent_id if latest_record else None,
        'runtimeProvider': latest_record.runtime_provider if latest_record else 'unknown',
        'runtimeModel': latest_record.runtime_model if latest_record else 'unknown',
        'runtimeAuthProfile': latest_record.runtime_auth_profile if latest_record else '',
        'runtimeAuthAccount': latest_record.runtime_auth_account if latest_record else '',
        'runtimeAccountId': latest_record.runtime_account_id if latest_record else '',
        'runtimeSessionKey': latest_record.session_key if latest_record else None,
        'totalTokens': total_tokens,
        'observedRuntimeTokens': observed_runtime_tokens,
        'productiveTokens': productive_tokens,
        'opsTokens': ops_tokens,
        'errorTokens': error_tokens,
        'recent5mTokens': recent_5m,
        'recent1hTokens': recent_1h,
        'recent24hTokens': recent_24h,
        'latestTurnTokens': latest_turn.get('tokens', 0),
        'latestTurnAt': latest_turn.get('timestamp').isoformat() if latest_turn.get('timestamp') else None,
        'latestTurnAgent': latest_turn.get('agentId'),
        'previousTurnTokens': previous_turn.get('tokens', 0),
        'previousTurnAt': previous_turn.get('timestamp').isoformat() if previous_turn.get('timestamp') else None,
        'previousTurnAgent': previous_turn.get('agentId'),
        'avgTokensPerSession': int(round(total_tokens / float(len(records)))) if records else 0,
        'avgTokensPerTurn': int(round(total_tokens / float(assistant_turns))) if assistant_turns else 0,
        'dailyBurnEstimate': daily_burn,
        'forecast30dTokens': forecast_30d,
        'updatedAt': data['loadedAt'],
        'sourcePath': data['path'],
        'sourceCount': len(data['sources']),
        'env': data['env'],
        'alert': alert,
    }


def _build_workstreams(records) -> List[Dict[str, Any]]:
    grouped = defaultdict(lambda: {'sessions': 0, 'totalTokens': 0, 'inputTokens': 0, 'outputTokens': 0})
    total = sum(record.total_tokens for record in records) or 1
    for record in records:
        item = grouped[record.workstream]
        item['sessions'] += 1
        item['totalTokens'] += record.total_tokens
        item['inputTokens'] += record.input_tokens
        item['outputTokens'] += record.output_tokens

    rows = []
    for name, item in grouped.items():
        rows.append({
            'name': name,
            'sessions': item['sessions'],
            'totalTokens': item['totalTokens'],
            'share': round((item['totalTokens'] / float(total)) * 100, 1),
        })
    return _sort_rows(rows, 'totalTokens')


def _build_projects(records) -> List[Dict[str, Any]]:
    grouped = defaultdict(lambda: {
        'sessions': 0,
        'assistantTurns': 0,
        'totalTokens': 0,
        'inputTokens': 0,
        'outputTokens': 0,
        'errorTokens': 0,
        'source': '',
        'kind': '',
        'latestActiveAt': None,
        'agentTokens': defaultdict(int),
    })
    for record in records:
        center = _effective_cost_center(record)
        item = grouped[center['name']]
        item['sessions'] += 1
        item['assistantTurns'] += record.assistant_turns
        item['totalTokens'] += record.total_tokens
        item['inputTokens'] += record.input_tokens
        item['outputTokens'] += record.output_tokens
        item['errorTokens'] += record.error_turn_tokens
        item['source'] = center['source']
        item['kind'] = center['kind']
        item['agentTokens'][record.agent_id] += record.total_tokens
        if record.last_active_at and (item['latestActiveAt'] is None or record.last_active_at > item['latestActiveAt']):
            item['latestActiveAt'] = record.last_active_at

    rows = []
    for name, item in grouped.items():
        owner_agent = max(item['agentTokens'].items(), key=lambda entry: entry[1])[0] if item['agentTokens'] else 'unknown'
        rows.append({
            'name': name,
            'kind': item['kind'],
            'source': item['source'],
            'sessions': item['sessions'],
            'assistantTurns': item['assistantTurns'],
            'totalTokens': item['totalTokens'],
            'avgTokensPerSession': int(round(item['totalTokens'] / float(item['sessions']))) if item['sessions'] else 0,
            'avgTokensPerTurn': int(round(item['totalTokens'] / float(item['assistantTurns']))) if item['assistantTurns'] else 0,
            'errorTokens': item['errorTokens'],
            'leadAgent': owner_agent,
            'latestActiveAt': item['latestActiveAt'].isoformat() if item['latestActiveAt'] else None,
        })
    return _sort_rows(rows, 'totalTokens')


def _build_agents(records) -> List[Dict[str, Any]]:
    grouped = defaultdict(lambda: {
        'sessions': 0,
        'totalTokens': 0,
        'inputTokens': 0,
        'outputTokens': 0,
        'recent24hTokens': 0,
        'recent5mTokens': 0,
        'errorTokens': 0,
        'assistantTurns': 0,
        'productiveTokens': 0,
        'latestActiveAt': None,
    })
    for record in records:
        item = grouped[record.agent_id]
        item['sessions'] += 1
        item['totalTokens'] += record.total_tokens
        item['inputTokens'] += record.input_tokens
        item['outputTokens'] += record.output_tokens
        item['recent24hTokens'] += record.recent_24h_tokens
        item['recent5mTokens'] += record.recent_5m_tokens
        item['errorTokens'] += record.error_turn_tokens
        item['assistantTurns'] += record.assistant_turns
        if _is_productive(record):
            item['productiveTokens'] += record.total_tokens
        if record.last_active_at and (item['latestActiveAt'] is None or record.last_active_at > item['latestActiveAt']):
            item['latestActiveAt'] = record.last_active_at

    rows = []
    for agent_id, item in grouped.items():
        rows.append({
            'agentId': agent_id,
            'sessions': item['sessions'],
            'assistantTurns': item['assistantTurns'],
            'totalTokens': item['totalTokens'],
            'recent24hTokens': item['recent24hTokens'],
            'recent5mTokens': item['recent5mTokens'],
            'avgTokensPerSession': int(round(item['totalTokens'] / float(item['sessions']))) if item['sessions'] else 0,
            'avgTokensPerTurn': int(round(item['totalTokens'] / float(item['assistantTurns']))) if item['assistantTurns'] else 0,
            'errorTokens': item['errorTokens'],
            'productiveShare': round((item['productiveTokens'] / float(item['totalTokens'])) * 100, 1) if item['totalTokens'] else 0,
            'latestActiveAt': item['latestActiveAt'].isoformat() if item['latestActiveAt'] else None,
        })
    return _sort_rows(rows, 'totalTokens')


def _build_models(records) -> List[Dict[str, Any]]:
    grouped = defaultdict(lambda: {'tokens': 0, 'turns': 0, 'provider': 'unknown'})
    for record in records:
        for model_name, usage in (record.model_breakdown or {}).items():
            item = grouped[model_name]
            item['tokens'] += int(usage.get('tokens', 0))
            item['turns'] += int(usage.get('turns', 0))
            item['provider'] = usage.get('provider') or item['provider']

    rows = []
    for model_name, item in grouped.items():
        rows.append({
            'model': model_name,
            'provider': item['provider'],
            'tokens': item['tokens'],
            'turns': item['turns'],
            'avgTokensPerTurn': int(round(item['tokens'] / float(item['turns']))) if item['turns'] else 0,
        })
    return _sort_rows(rows, 'tokens')


def _build_risk(records) -> Dict[str, Any]:
    hot_sessions = []
    for record in records:
        if record.recent_5m_tokens > 0 or record.error_turn_tokens > 0:
            hot_sessions.append({
                'agentId': record.agent_id,
                'sessionKey': record.session_key,
                'project': record.project,
                'workstream': record.workstream,
                'recent5mTokens': record.recent_5m_tokens,
                'errorTokens': record.error_turn_tokens,
                'lastActiveAt': record.last_active_at.isoformat() if record.last_active_at else None,
            })
    hot_sessions = sorted(
        hot_sessions,
        key=lambda row: (row['recent5mTokens'], row['errorTokens']),
        reverse=True,
    )

    threshold = 100000
    over_threshold = [row for row in hot_sessions if row['recent5mTokens'] >= threshold]
    if over_threshold:
        level = 'critical'
        message = '发现最近 5 分钟高消耗会话，建议立即止损排查'
    elif hot_sessions:
        level = 'warning'
        message = '存在错误暴露或波动会话，建议优先复盘前 3 项'
    else:
        level = 'normal'
        message = '近 5 分钟没有出现高消耗或错误暴露会话'

    return {
        'level': level,
        'threshold5mTokens': threshold,
        'message': message,
        'hotSessions': hot_sessions[:8],
    }


def _build_top_sessions(records, limit: int = 20) -> List[Dict[str, Any]]:
    rows = []
    for record in records:
        rows.append({
            'agentId': record.agent_id,
            'sessionKey': record.session_key,
            'project': record.project,
            'workstream': record.workstream,
            'type': record.session_type,
            'inputTokens': record.input_tokens,
            'outputTokens': record.output_tokens,
            'totalTokens': record.total_tokens,
            'errorTokens': record.error_turn_tokens,
            'lastActiveAt': record.last_active_at.isoformat() if record.last_active_at else None,
        })
    return _sort_rows(rows, 'totalTokens', limit)


def _build_insights(overview: Dict[str, Any], projects, agents, risk) -> List[Dict[str, str]]:
    insights = []
    total = overview['totalTokens'] or 1
    observed = overview['observedRuntimeTokens'] or 1
    ops_share = round((overview['opsTokens'] / float(total)) * 100, 1)
    error_share = round((overview['errorTokens'] / float(observed)) * 100, 1)

    if projects:
        top_project = projects[0]
        insights.append({
            'title': '最大成本中心',
            'detail': '{0} 当前消耗 {1:,} tokens，已成为主要预算口径。'.format(
                top_project['name'],
                top_project['totalTokens'],
            ),
        })
    if ops_share >= 50:
        insights.append({
            'title': '运维占比偏高',
            'detail': '内部运维占比 {0}% ，建议优先给高频任务补项目标签，避免 ROI 被埋没。'.format(ops_share),
        })
    if error_share >= 8:
        top_agent = agents[0] if agents else {'agentId': '未知'}
        insights.append({
            'title': '错误暴露需要压降',
            'detail': '观测到 {0}% 的错误暴露，先排查 {1} 的高频报错链路。'.format(error_share, top_agent['agentId']),
        })
    if risk['level'] == 'critical':
        hot = risk['hotSessions'][0]
        insights.append({
            'title': '红灯止损',
            'detail': '{0} 在最近 5 分钟内异常升温，建议立即停看问诊。'.format(hot['agentId']),
        })
    if not insights:
        insights.append({
            'title': '经营状态稳定',
            'detail': '当前没有出现高消耗红灯，建议下一步优先推动项目标签落地。',
        })
    return insights[:4]


def get_summary(range_name: str, agent_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    data = _filtered(range_name, agent_ids=agent_ids)
    overview = _build_overview(data)
    return {
        'range': data['range'],
        'sessions': overview['sessions'],
        'inputTokens': overview['inputTokens'],
        'outputTokens': overview['outputTokens'],
        'cacheReadTokens': overview['cacheReadTokens'],
        'cacheWriteTokens': overview['cacheWriteTokens'],
        'cacheBaseTokens': overview['cacheBaseTokens'],
        'cacheHitRate': overview['cacheHitRate'],
        'totalTokens': overview['totalTokens'],
        'observedRuntimeTokens': overview['observedRuntimeTokens'],
        'productiveTokens': overview['productiveTokens'],
        'opsTokens': overview['opsTokens'],
        'errorTokens': overview['errorTokens'],
        'recent5mTokens': overview['recent5mTokens'],
        'updatedAt': overview['updatedAt'],
        'sourcePath': overview['sourcePath'],
        'totalRawRows': data['totalRawRows'],
        'selectedAgents': agent_ids or [],
        'sourceCount': overview['sourceCount'],
        'warnings': [],
        'env': overview['env'],
        'alert': overview['alert'],
        'dailyBurnEstimate': overview['dailyBurnEstimate'],
        'forecast30dTokens': overview['forecast30dTokens'],
        'avgTokensPerSession': overview['avgTokensPerSession'],
        'activeAgents': overview['activeAgents'],
        'assistantTurns': overview['assistantTurns'],
        'avgTokensPerTurn': overview['avgTokensPerTurn'],
        'latestTurnTokens': overview['latestTurnTokens'],
        'latestTurnAt': overview['latestTurnAt'],
        'latestTurnAgent': overview['latestTurnAgent'],
        'previousTurnTokens': overview['previousTurnTokens'],
        'previousTurnAt': overview['previousTurnAt'],
        'previousTurnAgent': overview['previousTurnAgent'],
    }


def get_by_type(range_name: str, agent_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    data = _filtered(range_name, agent_ids=agent_ids)
    return {
        'range': data['range'],
        'items': _build_workstreams(data['records']),
        'updatedAt': data['loadedAt'],
        'warnings': [],
    }


def get_top_sessions(range_name: str, limit: int = 20, agent_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    data = _filtered(range_name, agent_ids=agent_ids)
    return {
        'range': data['range'],
        'items': _build_top_sessions(data['records'], limit),
        'updatedAt': data['loadedAt'],
        'warnings': [],
    }


def get_health(agent_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    payload = load_sessions(agent_ids=agent_ids)
    return {
        'ok': True,
        'sourcePath': payload['path'],
        'loadedAt': payload['loadedAt'],
        'totalRawRows': payload['totalRawRows'],
        'sourceCount': len(payload['sources']),
        'warnings': [],
    }


def get_office_status(focus_agent: str = '') -> Dict[str, Any]:
    payload = load_sessions(agent_ids=list(OFFICIAL_BOTS))
    latest_by_agent = _latest_records_by_agent(payload['records'])
    now = utc_now()
    items = []

    for agent_id in OFFICE_AGENT_ORDER:
        record = latest_by_agent.get(agent_id)
        state, label, detail = _office_state(record, now)
        items.append({
            'agentId': agent_id,
            'state': state,
            'stateLabel': label,
            'detail': detail,
            'workstream': record.workstream if record else '无观测',
            'latestActiveAt': record.last_active_at.isoformat() if record and record.last_active_at else None,
            'recent5mTokens': record.recent_5m_tokens if record else 0,
            'recent1hTokens': record.recent_1h_tokens if record else 0,
            'errorTokens': record.error_turn_tokens if record else 0,
            'latestTurnTokens': record.recent_turns[0]['tokens'] if record and record.recent_turns else 0,
            'runtimeModel': record.runtime_model if record else 'unknown',
            'runtimeProvider': record.runtime_provider if record else 'unknown',
            'runtimeAccount': record.runtime_auth_account if record else '',
            'sessionKey': record.session_key if record else '',
            'focused': bool(focus_agent and focus_agent == agent_id),
        })

    return {
        'updatedAt': payload['loadedAt'],
        'focusAgent': focus_agent,
        'env': payload.get('env', 'Unknown'),
        'items': items,
        'summary': {
            'total': len(items),
            'active': len([item for item in items if item['state'] not in {'idle', 'offline'}]),
            'busy': len([item for item in items if item['state'] in {'writing', 'executing', 'syncing', 'researching'}]),
            'error': len([item for item in items if item['state'] == 'error']),
        },
    }


def list_agents(range_name: str = 'all', agent_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    data = _filtered(range_name, agent_ids=agent_ids)
    return {'items': _build_agents(data['records'])}


def get_dashboard(range_name: str, agent_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    data = _filtered(range_name, agent_ids=agent_ids)
    overview = _build_overview(data)
    workstreams = _build_workstreams(data['records'])
    projects = _build_projects(data['records'])
    agents = _build_agents(data['records'])
    models = _build_models(data['records'])
    risk = _build_risk(data['records'])
    top_sessions = _build_top_sessions(data['records'], 20)
    insights = _build_insights(overview, projects, agents, risk)
    return {
        'range': data['range'],
        'overview': overview,
        'workstreams': workstreams,
        'projects': projects,
        'agents': agents,
        'models': models,
        'risk': risk,
        'topSessions': top_sessions,
        'insights': insights,
        'filters': {
            'selectedAgents': agent_ids or [],
            'availableAgents': [item['agentId'] for item in agents],
        },
    }
